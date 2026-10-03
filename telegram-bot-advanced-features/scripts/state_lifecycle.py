"""Runnable SQLAlchemy 2 async/aiosqlite lifecycle example, no network calls.

Uses SQLite-specific upsert. Real deployments should use migrations and the
chosen database dialect's conflict strategy, not schema creation on each boot.
"""
from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import BigInteger, DateTime, String, func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    joined: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    locale: Mapped[str] = mapped_column(String(20), default="en")


async def ensure_user(factory, user_id: int) -> User:
    if type(user_id) is not int or not 0 < user_id < 2**63:
        raise ValueError("invalid user ID")
    # A separate session per call/task; context managers commit/rollback/close.
    async with factory() as session:
        async with session.begin():
            await session.execute(insert(User).values(id=user_id, locale="en").on_conflict_do_nothing(index_elements=[User.id]))
            user = await session.scalar(select(User).where(User.id == user_id))
        return user  # expire_on_commit=False preserves already-loaded attributes.


async def demo():
    with tempfile.TemporaryDirectory() as temp:
        path = (Path(temp) / "demo.db").as_posix()
        engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            factory = async_sessionmaker(engine, expire_on_commit=False)
            users = await asyncio.gather(*(ensure_user(factory, 101) for _ in range(4)))
            assert all(user.id == 101 and user.locale == "en" for user in users)
            print("Async sessions persisted one user across concurrent upserts.")
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(demo())
