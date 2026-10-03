"""Run with uvicorn redirect_service:app; share RECIPE_DB with the bot."""
import asyncio
import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from recipe_store import Store, public_url

app = FastAPI()
store = Store(os.getenv("RECIPE_DB", "recipes.db"))


@app.get("/{code}")
async def redirect(code: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]{8}", code):
        raise HTTPException(404)
    url = await asyncio.to_thread(store.resolve, code)
    if url is None:
        raise HTTPException(404)
    return RedirectResponse(public_url(url), status_code=302,
                            headers={"Cache-Control": "no-store"})
