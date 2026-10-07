"""Persistencia SQLite para nao repetir promocoes no grupo."""
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS sent (
                   item_id TEXT PRIMARY KEY,
                   price REAL NOT NULL,
                   sent_at TEXT NOT NULL DEFAULT (datetime('now'))
               )"""
        )

    def should_send(self, item_id: str, price: float, repost_after_days: int = 3) -> bool:
        """Envia se nunca foi enviado, se o preco caiu, ou se ja passou `repost_after_days`."""
        row = self.conn.execute(
            "SELECT price, julianday('now') - julianday(sent_at) FROM sent WHERE item_id = ?",
            (item_id,),
        ).fetchone()
        if row is None:
            return True
        last_price, age_days = row
        return price < last_price or age_days >= repost_after_days

    def mark_sent(self, item_id: str, price: float) -> None:
        self.conn.execute(
            "INSERT INTO sent (item_id, price) VALUES (?, ?) "
            "ON CONFLICT(item_id) DO UPDATE SET price = excluded.price, sent_at = datetime('now')",
            (item_id, price),
        )
        self.conn.commit()
