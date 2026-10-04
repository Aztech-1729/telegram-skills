"""Small persistent recipe store; each operation owns and closes its connection."""
import secrets
import sqlite3
import time
import math
from urllib.parse import urlsplit


def public_url(value):
    if not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("Control characters are not accepted")
    parsed = urlsplit(value)
    try:
        parsed.port
    except ValueError as error:
        raise ValueError("Invalid URL port") from error
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Use an absolute HTTP(S) URL")
    if parsed.username or parsed.password or any(c.isspace() for c in value):
        raise ValueError("Credentials and whitespace are not accepted")
    return value


def text_parts(text, limit=4000):
    """Conservative plain-text chunks in UTF-16 units, without splitting a codepoint."""
    if type(limit) is not int or limit < 2:
        raise ValueError("Text limit must be at least two UTF-16 units")
    part, units = [], 0
    for char in text:
        width = 2 if ord(char) > 0xFFFF else 1
        if units + width > limit:
            yield "".join(part)
            part, units = [], 0
        part.append(char)
        units += width
    if part:
        yield "".join(part)


class Store:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS warns(
                    chat INTEGER, user INTEGER, count INTEGER,
                    PRIMARY KEY(chat,user));
                CREATE TABLE IF NOT EXISTS reminders(
                    id INTEGER PRIMARY KEY, chat INTEGER, text TEXT,
                    due INTEGER, done INTEGER NOT NULL DEFAULT 0,
                    user INTEGER, thread INTEGER, attempts INTEGER NOT NULL DEFAULT 0,
                    available INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT);
                CREATE TABLE IF NOT EXISTS quizzes(
                    id TEXT PRIMARY KEY, user INTEGER, chat INTEGER,
                    step INTEGER NOT NULL DEFAULT 0, score INTEGER NOT NULL DEFAULT 0,
                    expires INTEGER);
                CREATE TABLE IF NOT EXISTS scores(
                    user INTEGER PRIMARY KEY, score INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS seen(
                    feed TEXT, guid TEXT, PRIMARY KEY(feed,guid));
                CREATE TABLE IF NOT EXISTS urls(code TEXT PRIMARY KEY, url TEXT);
                CREATE TABLE IF NOT EXISTS delivery_pause(id INTEGER PRIMARY KEY, until INTEGER NOT NULL);
            """)
            # Migrate databases copied from an earlier starter under one write lock.
            db.execute("BEGIN IMMEDIATE")
            columns = {row[1] for row in db.execute("PRAGMA table_info(reminders)")}
            for name, definition in {"user": "INTEGER", "thread": "INTEGER",
                                     "attempts": "INTEGER NOT NULL DEFAULT 0",
                                     "available": "INTEGER NOT NULL DEFAULT 0",
                                     "failed": "INTEGER NOT NULL DEFAULT 0", "last_error": "TEXT"}.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE reminders ADD COLUMN {name} {definition}")

    def connect(self):
        # sqlite Connection context commits but does not close: use our wrapper.
        return ClosingConnection(self.path)

    def warn(self, chat, user):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO warns VALUES(?,?,1) ON CONFLICT(chat,user) "
                       "DO UPDATE SET count=count+1", (chat, user))
            return db.execute("SELECT count FROM warns WHERE chat=? AND user=?",
                              (chat, user)).fetchone()[0]

    def remind(self, chat, text, due, *, user=None, thread=None):
        with self.connect() as db:
            return db.execute("INSERT INTO reminders(chat,text,due,user,thread) VALUES(?,?,?,?,?)",
                              (chat, text, due, user, thread)).lastrowid

    def due(self, now):
        with self.connect() as db:
            if db.execute("SELECT 1 FROM delivery_pause WHERE id=1 AND until>?", (now,)).fetchone():
                return []
            return db.execute("SELECT id,chat,text,thread,attempts FROM reminders "
                              "WHERE done=0 AND failed=0 AND due<=? AND available<=? "
                              "ORDER BY due,id LIMIT 100", (now, now)).fetchall()

    def pause_delivery(self, now, delay):
        if type(delay) not in {int, float} or not math.isfinite(delay) or delay < 0:
            raise ValueError("Invalid delivery pause")
        with self.connect() as db:
            db.execute("INSERT INTO delivery_pause VALUES(1,?) ON CONFLICT(id) "
                       "DO UPDATE SET until=max(until,excluded.until)", (math.ceil(now + delay),))

    def delivered(self, reminder_id):
        with self.connect() as db:
            db.execute("UPDATE reminders SET done=1 WHERE id=?", (reminder_id,))

    def delivery_failed(self, reminder_id, error_name, now, delay):
        """Persist a bounded retry or terminal failure; do not store error bodies/secrets."""
        if delay is not None and (type(delay) not in {int, float} or not math.isfinite(delay) or delay < 0):
            raise ValueError("Invalid retry delay")
        with self.connect() as db:
            db.execute("UPDATE reminders SET attempts=attempts+1,last_error=?,available=?,"
                       "failed=CASE WHEN ? OR attempts+1>=5 THEN 1 ELSE 0 END WHERE id=? AND done=0",
                       (error_name, math.ceil(now + (delay or 0)), delay is None, reminder_id))

    def reminders(self, user, chat):
        with self.connect() as db:
            return db.execute("SELECT id,due,text,failed FROM reminders WHERE user=? AND chat=? "
                              "AND done=0 ORDER BY due,id LIMIT 20", (user, chat)).fetchall()

    def cancel_reminder(self, reminder_id, user, chat):
        with self.connect() as db:
            return db.execute("UPDATE reminders SET done=1 WHERE id=? AND user=? AND chat=? AND done=0",
                              (reminder_id, user, chat)).rowcount == 1

    def new_quiz(self, user, chat, now=None):
        quiz_id = secrets.token_hex(8)
        with self.connect() as db:
            db.execute("INSERT INTO quizzes(id,user,chat,expires) VALUES(?,?,?,?)",
                       (quiz_id, user, chat, int(time.time() if now is None else now)+3600))
        return quiz_id

    def answer(self, quiz_id, user, chat, step, choice, questions, now=None):
        """Validate ownership, expiry, order and choice, then score exactly once."""
        now = int(time.time() if now is None else now)
        if not 0 <= step < len(questions) or not 0 <= choice < len(questions[step][1]):
            raise ValueError("Invalid answer")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT user,chat,step,expires FROM quizzes WHERE id=?",
                             (quiz_id,)).fetchone()
            if row is None or row[:3] != (user, chat, step) or row[3] <= now:
                raise ValueError("This quiz is stale or belongs to another user")
            correct = choice == questions[step][2]
            db.execute("UPDATE quizzes SET step=step+1,score=score+? WHERE id=?",
                       (int(correct), quiz_id))
            if correct:
                db.execute("INSERT INTO scores VALUES(?,1) ON CONFLICT(user) "
                           "DO UPDATE SET score=score+1", (user,))
            return correct

    def seen(self, feed, guid):
        with self.connect() as db:
            return db.execute("SELECT 1 FROM seen WHERE feed=? AND guid=?", (feed, guid)).fetchone() is not None

    def mark_seen(self, feed, guid):
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO seen VALUES(?,?)", (feed, guid))

    def shorten(self, url):
        public_url(url)
        with self.connect() as db:
            for _ in range(5):
                code = secrets.token_urlsafe(6)
                try:
                    db.execute("INSERT INTO urls VALUES(?,?)", (code, url))
                    return code
                except sqlite3.IntegrityError:
                    continue
        raise RuntimeError("Could not allocate a URL code")

    def resolve(self, code):
        with self.connect() as db:
            row = db.execute("SELECT url FROM urls WHERE code=?", (code,)).fetchone()
        return None if row is None else row[0]


class ClosingConnection:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute("PRAGMA journal_mode=WAL")

    def __enter__(self):
        return self.db

    def __exit__(self, kind, value, traceback):
        try:
            if kind is None:
                self.db.commit()
            else:
                self.db.rollback()
        finally:
            self.db.close()


async def deliver_due(store, send, now, failure_policy=None, pause_on_error=None):
    """Single worker; optional policy isolates rows. Crash-after-send can duplicate."""
    import asyncio
    for reminder_id, chat, text, thread, attempts in await asyncio.to_thread(store.due, now):
        try:
            kwargs = {"message_thread_id": thread} if thread is not None else {}
            await send(chat, "Reminder: " + text, **kwargs)
        except Exception as error:
            if failure_policy is None:
                raise
            delay = failure_policy(error, attempts + 1)
            await asyncio.to_thread(store.delivery_failed, reminder_id, type(error).__name__, now, delay)
            if pause_on_error is not None and pause_on_error(error):
                if delay is None:
                    raise ValueError("A paused sender requires a retry delay")
                await asyncio.to_thread(store.pause_delivery, now, delay)
                break
        else:
            await asyncio.to_thread(store.delivered, reminder_id)
