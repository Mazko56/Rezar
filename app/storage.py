"""SQLite persistence for users, independent quiz sections, and admin image overrides.

Set BOT_DATA_DIR=/app/data on a Railway Volume to persist data across deployments.
Legacy ``people`` fields are retained, and old quiz progress is migrated lazily.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

FIELDS = {"stage", "car", "year", "budget", "phone", "contact_method", "completed", "view", "source", "manager_request"}
QUIZ_FIELDS = {"stage", "car", "year", "budget", "contact_method", "completed"}
ORIGINS = {"pick", "calc", "access"}


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
        view TEXT DEFAULT 'home', source TEXT, manager_request TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS quiz_sessions (
        telegram_id INTEGER NOT NULL,
        origin TEXT NOT NULL,
        stage TEXT NOT NULL DEFAULT 'car',
        car TEXT, year TEXT, budget TEXT, contact_method TEXT,
        completed INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (telegram_id, origin)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS media_overrides (
        screen TEXT PRIMARY KEY,
        telegram_file_id TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS admin_sessions (
        telegram_id INTEGER PRIMARY KEY,
        awaiting_photo TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS auction_credentials (
        credential_key TEXT PRIMARY KEY,
        credential_value TEXT NOT NULL
    )""")
    # Add metadata without removing any data from existing Railway volumes.
    columns={r['name'] for r in conn.execute('PRAGMA table_info(people)')}
    upgrades={
      'username':'TEXT','first_name':'TEXT','language_code':'TEXT',
      'first_start':'TEXT','last_activity':'TEXT','first_source':'TEXT',
      'last_source':'TEXT','start_param':'TEXT','phone_received_at':'TEXT',
      'crm_sent':'INTEGER NOT NULL DEFAULT 0','crm_lead_id':'TEXT','crm_sent_at':'TEXT'
    }
    for name, sqltype in upgrades.items():
        if name not in columns:
            conn.execute(f'ALTER TABLE people ADD COLUMN {name} {sqltype}')
    quiz_columns={r['name'] for r in conn.execute('PRAGMA table_info(quiz_sessions)')}
    if 'submission_seq' not in quiz_columns:
        conn.execute('ALTER TABLE quiz_sessions ADD COLUMN submission_seq INTEGER NOT NULL DEFAULT 0')
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


def _init_legacy_quiz(c, telegram_id: int, origin: str):
    exists = c.execute("SELECT 1 FROM quiz_sessions WHERE telegram_id=? AND origin=?", (telegram_id, origin)).fetchone()
    if exists:
        return
    legacy = c.execute("SELECT * FROM people WHERE telegram_id=?", (telegram_id,)).fetchone()
    if legacy and legacy["source"] == origin and (legacy["stage"] or legacy["completed"]):
        c.execute("""INSERT INTO quiz_sessions
            (telegram_id, origin, stage, car, year, budget, contact_method, completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (telegram_id, origin, legacy["stage"] or "car", legacy["car"], legacy["year"],
             legacy["budget"], legacy["contact_method"], legacy["completed"] or 0))
    else:
        c.execute("INSERT INTO quiz_sessions(telegram_id, origin) VALUES (?, ?)", (telegram_id, origin))


def read_quiz(telegram_id: int, origin: str) -> dict:
    if origin not in ORIGINS:
        raise ValueError("Invalid quiz origin")
    read(telegram_id)
    with _conn() as c:
        _init_legacy_quiz(c, telegram_id, origin)
        row = c.execute("SELECT * FROM quiz_sessions WHERE telegram_id=? AND origin=?", (telegram_id, origin)).fetchone()
    return dict(row)


def begin_quiz(telegram_id: int, origin: str) -> dict:
    """Resume incomplete quiz or start a new one after prior completion."""
    # Migrate the previous (legacy) active section before changing people.source.
    # Otherwise opening calc could make an unfinished legacy pick draft disappear.
    person = read(telegram_id)
    old_origin = person.get("source")
    if old_origin in ORIGINS and old_origin != origin:
        read_quiz(telegram_id, old_origin)
    previous = read_quiz(telegram_id, origin)
    with _conn() as c:
        if previous["completed"] or previous["stage"] == "done":
            c.execute("""UPDATE quiz_sessions SET stage='car', car=NULL, year=NULL,
                budget=NULL, contact_method=NULL, completed=0, submission_seq=submission_seq+1
                WHERE telegram_id=? AND origin=?""", (telegram_id, origin))
        c.execute("UPDATE people SET view='quiz', source=? WHERE telegram_id=?", (origin, telegram_id))
    return read_quiz(telegram_id, origin)


def update_quiz(telegram_id: int, origin: str, **values):
    if set(values) - QUIZ_FIELDS:
        raise ValueError("Invalid quiz field")
    read_quiz(telegram_id, origin)
    if not values:
        return
    keys = list(values)
    with _conn() as c:
        c.execute("UPDATE quiz_sessions SET " + ", ".join(f"{key}=?" for key in keys) +
                  " WHERE telegram_id=? AND origin=?", [values[k] for k in keys] + [telegram_id, origin])


def complete_quiz(telegram_id: int, origin: str):
    q = read_quiz(telegram_id, origin)
    update_quiz(telegram_id, origin, stage="done", completed=1)
    # Keep a copy in legacy columns; existing external integrations may read these.
    update(telegram_id, stage="done", car=q["car"], year=q["year"], budget=q["budget"],
           contact_method=q["contact_method"], completed=1, source=origin)


def has_completed_quiz(telegram_id: int) -> bool:
    p = read(telegram_id)
    with _conn() as c:
        row = c.execute("SELECT 1 FROM quiz_sessions WHERE telegram_id=? AND completed=1 LIMIT 1", (telegram_id,)).fetchone()
    return bool(row or p["completed"])


def get_photo_override(screen: str) -> str | None:
    with _conn() as c:
        row = c.execute("SELECT telegram_file_id FROM media_overrides WHERE screen=?", (screen,)).fetchone()
    return row["telegram_file_id"] if row else None


def set_photo_override(screen: str, file_id: str):
    with _conn() as c:
        c.execute("INSERT INTO media_overrides(screen, telegram_file_id) VALUES(?, ?) "
                  "ON CONFLICT(screen) DO UPDATE SET telegram_file_id=excluded.telegram_file_id", (screen, file_id))


def remove_photo_override(screen: str):
    with _conn() as c:
        c.execute("DELETE FROM media_overrides WHERE screen=?", (screen,))


def set_admin_pending(telegram_id: int, screen: str | None):
    with _conn() as c:
        c.execute("INSERT INTO admin_sessions(telegram_id, awaiting_photo) VALUES (?, ?) "
                  "ON CONFLICT(telegram_id) DO UPDATE SET awaiting_photo=excluded.awaiting_photo", (telegram_id, screen))


def get_admin_pending(telegram_id: int) -> str | None:
    with _conn() as c:
        row = c.execute("SELECT awaiting_photo FROM admin_sessions WHERE telegram_id=?", (telegram_id,)).fetchone()
    return row["awaiting_photo"] if row else None


# The admin can change individual logins/passwords without redeploying the code.
# SQLite data must reside on a private persistent volume, not in Git.
AUCTION_CREDENTIALS = {
    "HAPPYCAR_ID", "HAPPYCAR_PASSWORD", "DUOCAR_ID", "DUOCAR_PASSWORD",
    "JENO_ID", "JENO_PASSWORD", "GLOVIS_LOGIN", "GLOVIS_PASSWORD",
}


def set_auction_credential(key: str, value: str):
    if key not in AUCTION_CREDENTIALS:
        raise ValueError("Unknown auction credential")
    with _conn() as conn:
        conn.execute("""INSERT INTO auction_credentials(credential_key, credential_value)
                     VALUES(?, ?) ON CONFLICT(credential_key)
                     DO UPDATE SET credential_value=excluded.credential_value""", (key, value))


DEFAULT_AUCTION_CREDENTIALS = {
    "HAPPYCAR_ID": "abc",
    "HAPPYCAR_PASSWORD": "123456!",
    "DUOCAR_ID": "DUOCAR123",
    "DUOCAR_PASSWORD": "duocar123",
    "JENO_ID": "mit111",
    "JENO_PASSWORD": "1234",
    "GLOVIS_LOGIN": "bexguest2",
    "GLOVIS_PASSWORD": "Kurtka2@",
}


def get_auction_credential(key: str) -> str:
    if key not in AUCTION_CREDENTIALS:
        raise ValueError("Unknown auction credential")
    with _conn() as conn:
        row = conn.execute("SELECT credential_value FROM auction_credentials WHERE credential_key=?", (key,)).fetchone()
    return row["credential_value"] if row else os.environ.get(key) or DEFAULT_AUCTION_CREDENTIALS[key]


def get_admin_action(telegram_id: int) -> str | None:
    return get_admin_pending(telegram_id)


def record_user(user, *, start_param=None):
    # Upsert profile without resetting the original source.
    from datetime import datetime, timezone
    now=datetime.now(timezone.utc).isoformat()
    tid=user.id
    source=(start_param or '').strip() or None
    read(tid)
    with _conn() as c:
        c.execute('UPDATE people SET username=?,first_name=?,language_code=?, '
                  'first_start=COALESCE(first_start,?),last_activity=?, '
                  'first_source=COALESCE(first_source,?),last_source=COALESCE(?,last_source), '
                  'start_param=COALESCE(?,start_param) WHERE telegram_id=?',
          (user.username,user.first_name,user.language_code,now,now,source,source,source,tid))


def mark_phone_received(tid):
    with _conn() as c:
        c.execute('UPDATE people SET phone_received_at=COALESCE(phone_received_at,CURRENT_TIMESTAMP) WHERE telegram_id=?',(tid,))
