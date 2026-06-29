"""
logger.py – SQLite-backed trade journal.

Table: trades
  id          INTEGER PRIMARY KEY
  timestamp   TEXT    (ISO-8601)
  symbol      TEXT
  side        TEXT    ('BUY' | 'SELL' | 'CLOSE_SL' | 'CLOSE_TP')
  price       REAL
  qty         REAL
  pnl_usdt    REAL    (NULL for opening trades)
  order_id    TEXT
"""

import sqlite3
from datetime import datetime, timezone
import config


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(config.DB_PATH)


def init_db() -> None:
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT    NOT NULL,
                symbol     TEXT    NOT NULL,
                side       TEXT    NOT NULL,
                price      REAL    NOT NULL,
                qty        REAL    NOT NULL,
                pnl_usdt   REAL,
                order_id   TEXT
            )
        """)
        con.commit()


def log_trade(
    symbol: str,
    side: str,
    price: float,
    qty: float,
    pnl_usdt: float | None = None,
    order_id: str | None   = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        con.execute(
            "INSERT INTO trades (timestamp, symbol, side, price, qty, pnl_usdt, order_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (now, symbol, side, price, qty, pnl_usdt, order_id),
        )
        con.commit()


def get_history(limit: int = 50) -> list[dict]:
    with _conn() as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def clear_history() -> None:
    """Delete all trades from the database (fresh start)."""
    with _conn() as con:
        con.execute("DELETE FROM trades")
        con.commit()
