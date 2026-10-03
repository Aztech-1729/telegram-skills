"""Small persistent recipe store; each operation owns and closes its connection."""
import secrets
import sqlite3
import time
from urllib.parse import urlsplit


def public_url(value):
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Use an absolute HTTP(S) URL")
    if parsed.username or parsed.password or any(c.isspace() for c in value):
        raise ValueError("Credentials and whitespace are not accepted")
    return value


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
                    due INTEGER, done INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS quizzes(
                    id TEXT PRIMARY KEY, user INTEGER, chat INTEGER,
                    step INTEGER NOT NULL DEFAULT 0, score INTEGER NOT NULL DEFAULT 0,
                    expires INTEGER);
                CREATE TABLE IF NOT EXISTS scores(
                    user INTEGER PRIMARY KEY, score INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS seen(
                    feed TEXT, guid TEXT, PRIMARY KEY(feed,guid));
                CREATE TABLE IF NOT EXISTS urls(code TEXT PRIMARY KEY, url TEXT);
            """)

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

    def remind(self, chat, text, due):
        with self.connect() as db:
            return db.execute("INSERT INTO reminders(chat,text,due) VALUES(?,?,?)",
                              (chat, text, due)).lastrowid

    def due(self, now):
        with self.connect() as db:
            return db.execute("SELECT id,chat,text FROM reminders WHERE done=0 AND due<=? "
                              "ORDER BY due LIMIT 100", (now,)).fetchall()

    def delivered(self, reminder_id):
        with self.connect() as db:
            db.execute("UPDATE reminders SET done=1 WHERE id=?", (reminder_id,))

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


async def deliver_due(store, send, now):
    """Single worker; failures stay pending. Crash-after-send can duplicate delivery."""
    import asyncio
    for reminder_id, chat, text in await asyncio.to_thread(store.due, now):
        await send(chat, "Reminder: " + text)
        await asyncio.to_thread(store.delivered, reminder_id)
