from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import aiosqlite

from app import runtime


class RuntimeCompatibilityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "checkpoint.db"

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    async def test_open_checkpointer_supports_aiosqlite_without_is_alive(self) -> None:
        async with runtime._open_checkpointer(str(self.db_path)) as checkpointer:
            await checkpointer.setup()

        self.assertTrue(hasattr(aiosqlite.Connection, "is_alive"))


if __name__ == "__main__":
    unittest.main()
