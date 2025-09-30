import sqlite3
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def connect(db_path="pyreactx.db"):
    # DB lives in project root by default
    Path(db_path).touch(exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def exec(sql, params=(), db_path="pyreactx.db"):
    with connect(db_path) as c:
        c.execute(sql, params)

def query_all(sql, params=(), db_path="pyreactx.db"):
    with connect(db_path) as c:
        cur = c.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

def query_one(sql, params=(), db_path="pyreactx.db"):
    with connect(db_path) as c:
        cur = c.execute(sql, params)
        r = cur.fetchone()
        return dict(r) if r else None
