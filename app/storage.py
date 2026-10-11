"""Persistent quiz progress and contact consent in a small SQLite file.
For Railway attach a Volume at /app/data and set BOT_DATA_DIR=/app/data.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

FIELDS = {"stage", "car", "year", "budget", "phone", "contact_method", "completed", "view", "source", "manager_request"}


def _path():
    root = Path(os.environ.get("BOT_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data")))
    root.mkdir(parents=True, exist_ok=True)
    return root / "rezar.sqlite3"


@contextmanager
def _conn():
    conn = sqlite3.connect(_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("""CREATE TABLE IF NOT EXISTS people (
        telegram_id INTEGER PRIMARY KEY,
        stage TEXT, car TEXT, year TEXT, budget TEXT,
        phone TEXT, contact_method TEXT, completed INTEGER DEFAULT 0,
        view TEXT DEFAULT 'home', source TEXT,
        manager_request TEXT
    )""")
    conn.commit()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def read(telegram_id: int) -> dict:
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO people(telegram_id) VALUES (?)", (telegram_id,))
        row = c.execute("SELECT * FROM people WHERE telegram_id=?", (telegram_id,)).fetchone()
    return dict(row)


def update(telegram_id: int, **values):
    unknown = set(values) - FIELDS
    if unknown:
        raise ValueError(f"Unsupported fields: {sorted(unknown)}")
    read(telegram_id)
    if not values:
        return
    keys = list(values)
    sql = "UPDATE people SET " + ", ".join(f"{key}=?" for key in keys) + " WHERE telegram_id=?"
    with _conn() as c:
        c.execute(sql, [values[k] for k in keys] + [telegram_id])
        c.commit()


def close_quiz(telegram_id):
    update(telegram_id, stage="done", completed=1)
