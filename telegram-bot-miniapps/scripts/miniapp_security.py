"""Bot-token HMAC validation and a small persistent bearer-session todo store.

No Telegram calls. One connection per operation; SQLite is a single-host example.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qsl


def validate_init_data(raw: str, bot_token: str, *, now: int | None = None,
                       max_age: int = 300, future_skew: int = 30) -> dict:
    """Verify decoded, sorted Telegram initData; require an authenticated user.

    max_age/future_skew are application policies, not Telegram-defined constants.
    HMAC excludes only hash; Ed25519 third-party validation is a different flow.
    """
    if not bot_token or type(max_age) is not int or max_age <= 0 or future_skew < 0:
        raise ValueError("invalid authentication configuration")
    if not isinstance(raw, str) or not raw or len(raw.encode("utf-8")) > 16384:
        raise ValueError("invalid initData size")
    if re.search(r"%(?![0-9A-Fa-f]{2})", raw):
        raise ValueError("invalid percent encoding")
    try:
        fields = parse_qsl(raw, keep_blank_values=True, strict_parsing=True,
                           encoding="utf-8", errors="strict", max_num_fields=64)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid initData query") from exc
    keys = [key for key, _ in fields]
    if any(not key or "\n" in key or "\r" in key for key in keys) or len(keys) != len(set(keys)):
        raise ValueError("duplicate or invalid initData keys")
    data = dict(fields)
    received = data.pop("hash", "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", received):
        raise ValueError("missing or invalid hash")
    check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received.lower()):
        raise ValueError("invalid initData signature")
    try:
        auth_date = int(data["auth_date"])
        current = int(time.time()) if now is None else now
        if not current - max_age <= auth_date <= current + future_skew:
            raise ValueError("expired or future initData")
        user = json.loads(data["user"], object_pairs_hook=_unique_json)
        if not isinstance(user, dict) or type(user.get("id")) is not int or not 0 < user["id"] < 2**63:
            raise ValueError("invalid user ID")
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("missing or invalid authenticated user") from exc
    return {**data, "auth_date": auth_date, "user": user}


def _unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON keys")
        result[key] = value
    return result


class TodoStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    digest TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
                    expires INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                    text TEXT NOT NULL, created INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS todos_owner ON todos(user_id, id);
            """)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _digest(token: str) -> str:
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise PermissionError("invalid session")
        return hashlib.sha256(token.encode()).hexdigest()

    def issue_session(self, user_id: int, *, now: int, ttl: int = 3600) -> str:
        if type(user_id) is not int or not 0 < user_id < 2**63 or type(ttl) is not int or ttl <= 0:
            raise ValueError("invalid session configuration")
        token = secrets.token_urlsafe(32)
        with self._db() as db:
            db.execute("DELETE FROM sessions WHERE expires <= ?", (now,))
            db.execute("INSERT INTO sessions VALUES (?, ?, ?)",
                       (self._digest(token), user_id, now + ttl))
        return token

    def _owner(self, db, token: str, now: int) -> int:
        row = db.execute("SELECT user_id FROM sessions WHERE digest=? AND expires>?",
                         (self._digest(token), now)).fetchone()
        if row is None:
            raise PermissionError("expired or revoked session")
        return row[0]

    def add(self, token: str, text: str, *, now: int) -> int:
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 500:
            raise ValueError("todo must contain 1–500 characters")
        with self._db() as db:
            owner = self._owner(db, token, now)
            cursor = db.execute("INSERT INTO todos(user_id, text, created) VALUES (?, ?, ?)",
                                (owner, text.strip(), now))
            return cursor.lastrowid

    def authenticated_user(self, token: str, *, now: int) -> int:
        """Resolve a validated bearer session for related checkout/entitlement routes."""
        with self._db() as db:
            return self._owner(db, token, now)

    def list(self, token: str, *, now: int) -> list[dict]:
        with self._db() as db:
            owner = self._owner(db, token, now)
            return [{"id": row[0], "text": row[1]} for row in db.execute(
                "SELECT id, text FROM todos WHERE user_id=? ORDER BY id LIMIT 500", (owner,))]

    def delete(self, token: str, todo_id: int, *, now: int) -> bool:
        with self._db() as db:
            owner = self._owner(db, token, now)
            return db.execute("DELETE FROM todos WHERE id=? AND user_id=?",
                               (todo_id, owner)).rowcount == 1

    def revoke(self, token: str):
        with self._db() as db:
            db.execute("DELETE FROM sessions WHERE digest=?", (self._digest(token),))
