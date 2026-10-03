import hashlib
import hmac
import importlib.util
import json
import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from urllib.parse import urlencode

from miniapp_security import TodoStore, validate_init_data

TOKEN = "123:offline-fixture-secret"


def signed(*, user_id=101, auth_date=1000, name="A + B & 😀", extra=None):
    fields = {"auth_date": str(auth_date), "user": json.dumps({"id": user_id, "first_name": name}, ensure_ascii=False)}
    fields.update(extra or {})
    key = hmac.digest(b"WebAppData", TOKEN.encode(), "sha256")
    check = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    fields["hash"] = hmac.digest(key, check.encode(), "sha256").hex()
    return urlencode(fields)


class AuthTests(unittest.TestCase):
    def test_decoding_unicode_signature_and_unknown_signed_fields(self):
        value = validate_init_data(signed(extra={"signature": "future-field", "empty": ""}), TOKEN, now=1000)
        self.assertEqual(value["user"]["first_name"], "A + B & 😀")
        self.assertEqual(value["user"]["id"], 101)

    def test_tamper_duplicates_bad_encoding_and_user_id(self):
        good = signed()
        invalid = [good.replace("auth_date=1000", "auth_date=1001"), good + "&user=x",
                   good + "&hash=" + "a" * 64, good + "&%75ser=x", good + "&x=%ZZ",
                   good + "&x=%FF", signed(user_id=True), signed(user_id="101"), signed(user_id=-1)]
        for raw in invalid:
            with self.subTest(raw=raw[:60]), self.assertRaises(ValueError):
                validate_init_data(raw, TOKEN, now=1000)

    def test_freshness_future_and_wrong_bot(self):
        for raw, token in [(signed(auth_date=699), TOKEN), (signed(auth_date=1031), TOKEN), (signed(), "wrong-token")]:
            with self.assertRaises(ValueError):
                validate_init_data(raw, token, now=1000)
        self.assertEqual(validate_init_data(signed(auth_date=700), TOKEN, now=1000)["auth_date"], 700)


class StoreTests(unittest.TestCase):
    def test_persistent_session_isolation_expiry_revocation_and_hash_storage(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "todos.db"
            store = TodoStore(path)
            first = store.issue_session(101, now=1000, ttl=100)
            second = store.issue_session(202, now=1000)
            record = store.add(first, "<script>not HTML</script>", now=1001)
            reopened = TodoStore(path)
            self.assertEqual(reopened.authenticated_user(first, now=1002), 101)
            self.assertEqual(reopened.authenticated_user(second, now=1002), 202)
            self.assertEqual(len(reopened.list(first, now=1002)), 1)
            self.assertEqual(reopened.list(second, now=1002), [])
            self.assertFalse(reopened.delete(second, record, now=1002))
            self.assertTrue(reopened.delete(first, record, now=1002))
            with self.assertRaises(PermissionError):
                reopened.list("101", now=1002)
            with closing(sqlite3.connect(path)) as db:
                digests = [row[0] for row in db.execute("SELECT digest FROM sessions")]
            self.assertNotIn(first, digests)
            self.assertIn(hashlib.sha256(first.encode()).hexdigest(), digests)
            with self.assertRaises(PermissionError):
                reopened.list(first, now=1100)
            with self.assertRaises(PermissionError):
                reopened.authenticated_user(first, now=1100)
            reopened.revoke(second)
            with self.assertRaises(PermissionError):
                reopened.authenticated_user(second, now=1002)
            with self.assertRaises(PermissionError):
                reopened.add(second, "blocked", now=1002)


class HTTPTests(unittest.TestCase):
    def test_login_authorization_persistence_and_public_file_boundary(self):
        from fastapi.testclient import TestClient
        app_path = Path(__file__).resolve().parents[1] / "assets" / "todo" / "app.py"
        spec = importlib.util.spec_from_file_location("todo_example", app_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        origin = "https://app.example.com"
        with tempfile.TemporaryDirectory() as temp:
            db_path = str(Path(temp) / "todo.db")
            with TestClient(module.create_app(TOKEN, origin, db_path)) as client:
                self.assertEqual(client.post("/api/login", json={"initData": signed(auth_date=int(time.time()))}).status_code, 403)
                headers = {"Origin": origin}
                login = client.post("/api/login", headers=headers, json={"initData": signed(auth_date=int(time.time()))})
                self.assertEqual(login.status_code, 200)
                auth = {**headers, "Authorization": "Bearer " + login.json()["token"]}
                self.assertEqual(client.get("/api/todos").status_code, 401)
                self.assertEqual(client.post("/api/todos", headers=auth, json={"text": "persisted"}).status_code, 201)
                self.assertEqual(client.post("/api/todos", headers=auth, json={"text": "bad", "session": 202}).status_code, 422)
                self.assertEqual(client.get("/app.py").status_code, 404)
                self.assertEqual(client.get("/todos.sqlite3").status_code, 404)
                # Query parameters cannot turn a public asset route into arbitrary file reads.
                public = client.get("/?path=" + str(app_path))
                self.assertIn("<!doctype html>", public.text)
                self.assertNotIn("def create_app", public.text)
            with TestClient(module.create_app(TOKEN, origin, db_path)) as restarted:
                self.assertEqual(restarted.get("/api/todos", headers=auth).json()["todos"][0]["text"], "persisted")
                self.assertEqual(restarted.post("/api/logout", headers=auth).status_code, 200)
                self.assertEqual(restarted.get("/api/todos", headers=auth).status_code, 401)


if __name__ == "__main__":
    unittest.main()
