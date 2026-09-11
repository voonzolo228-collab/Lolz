"""
SQLite шар зберігання даних (aiosqlite).

SQLite обраний, бо навантаження одно-користувацьке/невелика кількість
користувачів, немає паралельних записів під високим навантаженням,
і не потрібен окремий сервер БД. PostgreSQL мав би сенс лише якщо
бот масштабується на багато одночасних користувачів з високим write
навантаженням - для цього завдання це не так.
"""
import json
import logging
import time
from typing import Any, Optional

import aiosqlite

logger = logging.getLogger("database")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    monitoring_enabled INTEGER NOT NULL DEFAULT 0,
    interval_seconds INTEGER NOT NULL DEFAULT 30,
    max_purchase_price REAL,
    min_profit_ton REAL DEFAULT 20,
    min_opportunity_score INTEGER DEFAULT 70,
    price_min REAL,
    price_max REAL,
    collections_json TEXT DEFAULT '[]',
    notifications_enabled INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS seen_gifts (
    chat_id INTEGER NOT NULL,
    gift_id TEXT NOT NULL,
    last_price REAL,
    last_notified_at REAL NOT NULL,
    PRIMARY KEY (chat_id, gift_id)
);
"""


class Database:
    def __init__(self, path: str):
        self._path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()
        logger.info("База даних підключена: %s", self._path)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    async def get_or_create_user(self, chat_id: int) -> dict[str, Any]:
        assert self._conn
        cur = await self._conn.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
        row = await cur.fetchone()
        if row:
            return dict(row)
        await self._conn.execute(
            "INSERT INTO users (chat_id, created_at) VALUES (?, ?)",
            (chat_id, time.time()),
        )
        await self._conn.commit()
        cur = await self._conn.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
        row = await cur.fetchone()
        return dict(row)

    async def update_user(self, chat_id: int, **fields: Any) -> None:
        assert self._conn
        if not fields:
            return
        if "collections" in fields:
            fields["collections_json"] = json.dumps(fields.pop("collections"))
        columns = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [chat_id]
        await self._conn.execute(f"UPDATE users SET {columns} WHERE chat_id = ?", values)
        await self._conn.commit()

    async def all_active_users(self) -> list[dict[str, Any]]:
        assert self._conn
        cur = await self._conn.execute("SELECT * FROM users WHERE monitoring_enabled = 1")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def get_seen(self, chat_id: int, gift_id: str) -> Optional[dict[str, Any]]:
        assert self._conn
        cur = await self._conn.execute(
            "SELECT * FROM seen_gifts WHERE chat_id = ? AND gift_id = ?", (chat_id, gift_id)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def mark_seen(self, chat_id: int, gift_id: str, price: Optional[float]) -> None:
        assert self._conn
        await self._conn.execute(
            """
            INSERT INTO seen_gifts (chat_id, gift_id, last_price, last_notified_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, gift_id) DO UPDATE SET
                last_price = excluded.last_price,
                last_notified_at = excluded.last_notified_at
            """,
            (chat_id, gift_id, price, time.time()),
        )
        await self._conn.commit()

    async def cleanup_old_seen(self, older_than_seconds: int = 7 * 24 * 3600) -> None:
        assert self._conn
        cutoff = time.time() - older_than_seconds
        await self._conn.execute("DELETE FROM seen_gifts WHERE last_notified_at < ?", (cutoff,))
        await self._conn.commit()
