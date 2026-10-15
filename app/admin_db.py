"""Storage for Telegram Mini App administration. Existing bot database remains compatible."""
import os, sqlite3, json, datetime
from pathlib import Path
from contextlib import contextmanager
ROOT_ID = 5138418509

def db_path():
    p = Path(os.environ.get('BOT_DATA_DIR', str(Path(__file__).resolve().parent.parent/'data')))
    p.mkdir(parents=True,exist_ok=True)
    return p/'rezar.sqlite3'

@contextmanager
def connection():
    c=sqlite3.connect(db_path(),timeout=20)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA busy_timeout=20000')
    c.executescript('''
    CREATE TABLE IF NOT EXISTS mini_admins(id INTEGER PRIMARY KEY, role TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS mini_content(key TEXT PRIMARY KEY, body TEXT, media_file_id TEXT, buttons_json TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS mini_labels(code TEXT PRIMARY KEY, utm_source TEXT, utm_medium TEXT, utm_campaign TEXT, utm_content TEXT, utm_term TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS mini_broadcasts(id INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT, media_file_id TEXT, state TEXT DEFAULT 'draft', created_by INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, sent INTEGER DEFAULT 0, failed INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS mini_delivery(id INTEGER PRIMARY KEY AUTOINCREMENT, broadcast_id INTEGER, recipient INTEGER, status TEXT DEFAULT 'pending', error TEXT, UNIQUE(broadcast_id,recipient));
    CREATE TABLE IF NOT EXISTS mini_crm_issues(id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id TEXT, error TEXT, status TEXT DEFAULT 'pending', updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    ''')
    c.execute('INSERT OR IGNORE INTO mini_admins(id,role) VALUES (?,?)',(ROOT_ID,'owner'))
    c.commit()
    try: yield c
    finally:
        c.commit(); c.close()

def role(tid):
    with connection() as c:
        r=c.execute('SELECT role FROM mini_admins WHERE id=?',(tid,)).fetchone()
    return r['role'] if r else None

def can(tid, permission):
    r=role(tid)
    if r=='owner':return True
    if r=='admin':return permission != 'admins'
    return r=='marketer' and permission in ('labels','stats')

def list_content():
    with connection() as c: return [dict(x) for x in c.execute('SELECT * FROM mini_content ORDER BY key')]

def get_content(key):
    with connection() as c:
        r=c.execute('SELECT * FROM mini_content WHERE key=?',(key,)).fetchone()
    return dict(r) if r else None
