"""Offline retry classification, secret checks and leased single-host outbox.

No Telegram calls. Leases do not make external delivery exactly once.
"""
from __future__ import annotations

import hmac
import json
import math
import re
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path


def valid_webhook_secret(configured: str, received: str | None) -> bool:
    if not isinstance(configured, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", configured):
        raise ValueError("invalid configured webhook secret")
    return isinstance(received, str) and hmac.compare_digest(configured.encode(), received.encode())


@dataclass(frozen=True)
class RetryDecision:
    action: str
    delay: float = 0


def _finite_number(value, name):
    try:
        valid = type(value) in {int, float} and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be finite")
    return value


def retry_decision(kind: str, attempt: int, *, max_attempts: int = 4,
                   retry_after: int | float | timedelta | None = None,
                   safe_replay: bool = False) -> RetryDecision:
    if type(attempt) is not int or type(max_attempts) is not int or not 1 <= attempt <= max_attempts:
        raise ValueError("attempt must be inside a positive retry budget")
    if type(safe_replay) is not bool:
        raise ValueError("safe_replay must be a deliberate Boolean")
    if kind == "recipient_blocked":
        return RetryDecision("blocked")
    if kind in {"network", "timeout", "server_error"} and not safe_replay:
        return RetryDecision("uncertain")
    if kind not in {"rate_limit", "network", "timeout", "server_error"}:
        return RetryDecision("failed")
    if kind == "rate_limit":
        seconds = retry_after.total_seconds() if isinstance(retry_after, timedelta) else retry_after
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError("valid retry_after is required")
        delay = float(seconds) + 0.1
    else:
        delay = min(2 ** min(attempt - 1, 6), 60)
    return RetryDecision("failed") if attempt >= max_attempts else RetryDecision("retry", delay)


class Outbox:
    """SQLite demo with unique dedupe keys, lease fencing and replay policy."""
    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS outbox (
                    id INTEGER PRIMARY KEY, dedupe_key TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL, safe_replay INTEGER NOT NULL,
                    state TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL, available REAL NOT NULL,
                    lease_until REAL, lease_token TEXT);
                CREATE INDEX IF NOT EXISTS outbox_ready ON outbox(state,available,id);
            """)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def enqueue(self, key: str, payload: dict, *, now: float, safe_replay: bool = False, max_attempts: int = 4) -> int:
        if not isinstance(key, str) or not key or not isinstance(payload, dict) or type(max_attempts) is not int or max_attempts < 1:
            raise ValueError("invalid job")
        _finite_number(now, "now")
        if type(safe_replay) is not bool:
            raise ValueError("safe_replay must be a deliberate Boolean")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT id,payload,safe_replay,max_attempts FROM outbox WHERE dedupe_key=?", (key,)).fetchone()
            if old:
                if (old["payload"], old["safe_replay"], old["max_attempts"]) != (encoded, int(safe_replay), max_attempts):
                    raise ValueError("dedupe key conflicts with an existing job")
                return old["id"]
            return db.execute("""INSERT INTO outbox(dedupe_key,payload,safe_replay,max_attempts,available)
                                 VALUES (?,?,?,?,?)""", (key, encoded, int(safe_replay), max_attempts, now)).lastrowid

    def claim(self, *, now: float, lease_seconds: float = 30) -> dict | None:
        _finite_number(now, "now")
        _finite_number(lease_seconds, "lease_seconds")
        _finite_number(now + lease_seconds, "lease end")
        if lease_seconds <= 0:
            raise ValueError("positive lease required")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            # A crashed non-idempotent task may already have reached its external receiver.
            db.execute("""UPDATE outbox SET state='uncertain',lease_token=NULL
                          WHERE state='inflight' AND lease_until<=? AND safe_replay=0""", (now,))
            db.execute("""UPDATE outbox SET state='failed',lease_token=NULL
                          WHERE attempts>=max_attempts AND
                          (state='pending' OR (state='inflight' AND lease_until<=?))""", (now,))
            row = db.execute("""SELECT * FROM outbox WHERE attempts<max_attempts AND
                              ((state='pending' AND available<=?) OR
                               (state='inflight' AND lease_until<=? AND safe_replay=1))
                              ORDER BY available,id LIMIT 1""", (now, now)).fetchone()
            if row is None:
                return None
            token = secrets.token_hex(16)
            db.execute("""UPDATE outbox SET state='inflight',attempts=attempts+1,
                          lease_until=?,lease_token=? WHERE id=?""", (now + lease_seconds, token, row["id"]))
            return {**dict(row), "payload": json.loads(row["payload"]), "state": "inflight",
                    "attempts": row["attempts"] + 1, "lease_token": token, "lease_until": now + lease_seconds}

    def complete(self, job_id: int, token: str, *, now: float) -> bool:
        _finite_number(now, "now")
        with self._db() as db:
            return db.execute("""UPDATE outbox SET state='sent',lease_token=NULL WHERE id=?
                              AND state='inflight' AND lease_token=? AND lease_until>?""",
                              (job_id, token, now)).rowcount == 1

    def resolve_attempt(self, job_id: int, token: str, decision: RetryDecision, *, now: float) -> bool:
        _finite_number(now, "now")
        _finite_number(decision.delay, "delay")
        _finite_number(now + decision.delay, "retry time")
        states = {"retry": "pending", "failed": "failed", "blocked": "blocked", "uncertain": "uncertain"}
        if decision.action not in states or not math.isfinite(decision.delay) or decision.delay < 0:
            raise ValueError("invalid retry decision")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""SELECT attempts,max_attempts FROM outbox WHERE id=? AND state='inflight'
                                AND lease_token=? AND lease_until>?""", (job_id, token, now)).fetchone()
            if row is None:
                return False
            state = states[decision.action]
            if state == "pending" and row["attempts"] >= row["max_attempts"]:
                state = "failed"
            db.execute("UPDATE outbox SET state=?,available=?,lease_token=NULL,lease_until=NULL WHERE id=?",
                       (state, now + decision.delay, job_id))
            return True

    def summary(self, *, now: float) -> dict:
        """Small operational view with no payloads, webhook secrets or lease tokens."""
        _finite_number(now, "now")
        with self._db() as db:
            states = dict(db.execute("SELECT state,count(*) FROM outbox GROUP BY state").fetchall())
            oldest = db.execute("SELECT min(available) FROM outbox WHERE state='pending' AND available<=?",
                                (now,)).fetchone()[0]
        return {"states": states, "oldest_due_age": None if oldest is None else now - oldest}

    def state(self, job_id: int) -> str:
        with self._db() as db:
            row = db.execute("SELECT state FROM outbox WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            return row["state"]
