import sqlite3
import datetime
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deals (
                    deal_id TEXT PRIMARY KEY,
                    creator_id INTEGER NOT NULL,
                    seller_id INTEGER NOT NULL,
                    buyer_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def register_user(self, user_id: int, username: Optional[str]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            conn.commit()

    def create_deal(
        self, deal_id: str, creator_id: int, seller_id: int, buyer_id: int, amount: float, description: str
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO deals (deal_id, creator_id, seller_id, buyer_id, amount, description, status)
                VALUES (?, ?, ?, ?, ?, ?, 'CREATED')
                """,
                (deal_id, creator_id, seller_id, buyer_id, amount, description)
            )
            conn.commit()

    def get_deal(self, deal_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_deal_status(self, deal_id: str, new_status: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE deals SET status = ? WHERE deal_id = ?", (new_status, deal_id))
            conn.commit()

    def get_user_deals(self, user_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM deals 
                WHERE seller_id = ? OR buyer_id = ?
                ORDER BY created_at DESC
                """,
                (user_id, user_id)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_all_deals(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deals ORDER BY created_at DESC LIMIT 50")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
