"""Offline, atomic one-time credit fulfillment; never calls Telegram.

Copy into an application's service layer. Subscription/refund business policy is
deliberately separate. Completed refund reconciliation can create a debt balance.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


class PaymentLedger:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS orders (
                    payload TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
                    currency TEXT NOT NULL, amount INTEGER NOT NULL,
                    units INTEGER NOT NULL, expires INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS payments (
                    charge_id TEXT PRIMARY KEY, payload TEXT NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL, currency TEXT NOT NULL,
                    amount INTEGER NOT NULL, refunded INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS balances (
                    user_id INTEGER PRIMARY KEY, units INTEGER NOT NULL);
            """)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def create_order(self, payload: str, user_id: int, amount: int, units: int, *, expires: int):
        if not isinstance(payload, str) or not 1 <= len(payload.encode()) <= 128:
            raise ValueError("payload must contain 1–128 UTF-8 bytes")
        if type(user_id) is not int or not 0 < user_id < 2**63:
            raise ValueError("invalid user ID")
        if type(amount) is not int or not 0 < amount < 2**63 or type(units) is not int or not 0 < units < 2**63:
            raise ValueError("positive SQLite integer amount and units required")
        if type(expires) is not int or not 0 < expires < 2**63:
            raise ValueError("positive integer checkout expiry required")
        with self._db() as db:
            db.execute("INSERT INTO orders VALUES (?, ?, 'XTR', ?, ?, ?)",
                       (payload, user_id, amount, units, expires))

    def validate_checkout(self, payload: str, user_id: int, currency: str, amount: int, *, now: int) -> bool:
        """Application-level availability check; successful payment is still authoritative."""
        if type(user_id) is not int or type(amount) is not int:
            return False
        with self._db() as db:
            return db.execute("""
                SELECT 1 FROM orders o WHERE payload=? AND user_id=?
                AND currency=? AND amount=? AND expires>?
                AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.payload=o.payload)
            """, (payload, user_id, currency, amount, now)).fetchone() is not None

    def accept_payment(self, charge_id: str, payload: str, user_id: int,
                       currency: str, amount: int) -> bool:
        """Return True only on first atomic delivery; reject mismatched replays.

        Does not reject a paid order merely because its pre-checkout window ended.
        A second unique charge for one order requires reconciliation/refund, not
        a second automatic grant. This ledger is specifically for one-time orders.
        """
        if not isinstance(charge_id, str) or not charge_id or type(amount) is not int or type(user_id) is not int:
            raise ValueError("invalid payment fields")
        received = (payload, user_id, currency, amount)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            duplicate = db.execute("SELECT payload, user_id, currency, amount FROM payments WHERE charge_id=?",
                                   (charge_id,)).fetchone()
            if duplicate is not None:
                if duplicate != received:
                    raise ValueError("charge replay conflicts with recorded payment")
                return False
            order = db.execute("SELECT user_id, currency, amount, units FROM orders WHERE payload=?",
                               (payload,)).fetchone()
            if order is None or order[:3] != received[1:]:
                raise ValueError("payment does not match server order")
            if db.execute("SELECT 1 FROM payments WHERE payload=?", (payload,)).fetchone():
                raise ValueError("unexpected second charge: reconcile and consider refund")
            db.execute("INSERT INTO payments(charge_id,payload,user_id,currency,amount) VALUES (?,?,?,?,?)",
                       (charge_id, *received))
            db.execute("""INSERT INTO balances(user_id,units) VALUES (?,?)
                          ON CONFLICT(user_id) DO UPDATE SET units=units+excluded.units""",
                       (user_id, order[3]))
            return True

    def record_completed_refund(self, charge_id: str, user_id: int, *,
                                payload: str | None = None, currency: str | None = None,
                                amount: int | None = None) -> bool:
        """Reconcile trusted refund confirmation; this does not request a refund.

        An application must decide how consumed credits/debt affect access.
        """
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""SELECT p.user_id,p.refunded,o.units,p.payload,p.currency,p.amount FROM payments p
                               JOIN orders o USING(payload) WHERE p.charge_id=?""", (charge_id,)).fetchone()
            if row is None or type(user_id) is not int or row[0] != user_id:
                raise ValueError("refund does not match payment user")
            # API success can be reconciled from the stored request. A refund
            # event supplies all three fields and must match before reversal.
            if any(value is not None for value in (payload, currency, amount)):
                if type(amount) is not int or row[3:] != (payload, currency, amount):
                    raise ValueError("refund event conflicts with recorded payment")
            if row[1]:
                return False
            db.execute("UPDATE payments SET refunded=1 WHERE charge_id=?", (charge_id,))
            db.execute("UPDATE balances SET units=units-? WHERE user_id=?", (row[2], user_id))
            return True

    def balance(self, user_id: int) -> int:
        with self._db() as db:
            row = db.execute("SELECT units FROM balances WHERE user_id=?", (user_id,)).fetchone()
            return row[0] if row else 0
