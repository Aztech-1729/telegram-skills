import asyncio
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from state_lifecycle import Base, User, ensure_user


class AsyncStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_isolation_upsert_and_reopen(self):
        with tempfile.TemporaryDirectory() as temp:
            url = f"sqlite+aiosqlite:///{(Path(temp) / 'state.db').as_posix()}"
            engine = create_async_engine(url)
            try:
                async with engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)
                factory = async_sessionmaker(engine, expire_on_commit=False)
                users = await asyncio.gather(*(ensure_user(factory, 101) for _ in range(8)))
                self.assertTrue(all(user.id == 101 for user in users))
                async with factory() as session:
                    self.assertEqual(await session.scalar(select(func.count()).select_from(User)), 1)
                with self.assertRaises(ValueError):
                    await ensure_user(factory, True)
            finally:
                await engine.dispose()
            reopened = create_async_engine(url)
            try:
                factory = async_sessionmaker(reopened, expire_on_commit=False)
                async with factory() as session:
                    user = await session.get(User, 101)
                    self.assertEqual(user.locale, "en")
                    self.assertIsNotNone(user.joined)
            finally:
                await reopened.dispose()


if __name__ == "__main__":
    unittest.main()
