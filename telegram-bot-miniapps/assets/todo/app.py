"""Runnable single-host example; HTTPS/rate limiting belong to the deployment.

From this directory: uvicorn app:app_factory --factory --host 127.0.0.1
Set TELEGRAM_BOT_TOKEN and MINIAPP_ORIGIN (the exact public HTTPS origin).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from miniapp_security import TodoStore, validate_init_data


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    initData: str = Field(min_length=1, max_length=16384)


class NewTodo(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1, max_length=500)


def create_app(bot_token: str, origin: str, db_path: str) -> FastAPI:
    parsed = urlsplit(origin)
    if not bot_token or parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("bot token and exact HTTPS origin are required")
    store = TodoStore(db_path)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def guards(request: Request, call_next):
        # Same-origin deployment, bearer auth rather than ambient cookies.
        # Reverse proxy must enforce an actual body limit (Content-Length may be absent).
        from starlette.responses import JSONResponse
        if request.method in {"POST", "DELETE"} and request.headers.get("origin") != origin:
            return JSONResponse({"detail": "origin rejected"}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://telegram.org; "
            "style-src 'self'; connect-src 'self'; img-src 'self' data:; "
            "object-src 'none'; base-uri 'none'"
        )
        return response

    def bearer(header: str | None) -> str:
        if header is None or not header.startswith("Bearer "):
            raise HTTPException(401, "session required")
        return header[7:]

    def auth_error(exc):
        raise HTTPException(401, "invalid or expired credentials") from exc

    @app.post("/api/login")
    def login(body: Login):
        now = int(time.time())
        try:
            data = validate_init_data(body.initData, bot_token, now=now)
        except ValueError as exc:
            auth_error(exc)
        return {"token": store.issue_session(data["user"]["id"], now=now),
                "name": data["user"].get("first_name", "User")}

    @app.get("/api/todos")
    def list_todos(authorization: str | None = Header(default=None)):
        try:
            return {"todos": store.list(bearer(authorization), now=int(time.time()))}
        except PermissionError as exc:
            auth_error(exc)

    @app.post("/api/todos", status_code=201)
    def add_todo(body: NewTodo, authorization: str | None = Header(default=None)):
        try:
            return {"id": store.add(bearer(authorization), body.text, now=int(time.time()))}
        except PermissionError as exc:
            auth_error(exc)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.delete("/api/todos/{todo_id}")
    def delete_todo(todo_id: int, authorization: str | None = Header(default=None)):
        try:
            deleted = store.delete(bearer(authorization), todo_id, now=int(time.time()))
        except PermissionError as exc:
            auth_error(exc)
        if not deleted:
            raise HTTPException(404, "todo not found")
        return {"ok": True}

    @app.post("/api/logout")
    def logout(authorization: str | None = Header(default=None)):
        try:
            store.revoke(bearer(authorization))
        except PermissionError as exc:
            auth_error(exc)
        return {"ok": True}

    # Deliberately serve only public assets, never a directory containing app.py/DB.
    def public_asset(filename, media_type):
        path = Path(__file__).parent / filename
        def serve():
            return FileResponse(path, media_type=media_type)
        return serve

    for route, filename, media_type in (
        ("/", "index.html", "text/html"),
        ("/app.js", "app.js", "application/javascript"),
        ("/style.css", "style.css", "text/css"),
    ):
        app.add_api_route(route, public_asset(filename, media_type), methods=["GET"], include_in_schema=False)
    return app


def app_factory():
    return create_app(os.environ["TELEGRAM_BOT_TOKEN"], os.environ["MINIAPP_ORIGIN"],
                      os.environ.get("MINIAPP_DB", "todos.sqlite3"))
