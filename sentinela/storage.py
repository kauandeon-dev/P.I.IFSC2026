"""Persistência em SQLite: usuários, configurações, backups, execuções e logs."""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

from . import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Cada execução (backup, restauração ou verificação) tem seu próprio log.
CREATE TABLE IF NOT EXISTS executions (
    id          INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL,          -- backup | restore | verify
    trigger     TEXT NOT NULL,          -- auto | manual | pre-restore
    backup_id   TEXT,
    sgbd        TEXT,
    dbname      TEXT,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL           -- running | success | error
);

CREATE TABLE IF NOT EXISTS log_lines (
    id           INTEGER PRIMARY KEY,
    execution_id INTEGER NOT NULL REFERENCES executions(id),
    ts           TEXT NOT NULL,
    level        TEXT NOT NULL,         -- INFO | OK | WARN | ERRO
    message      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_log_exec ON log_lines(execution_id);

CREATE TABLE IF NOT EXISTS backups (
    id           TEXT PRIMARY KEY,
    execution_id INTEGER,
    trigger      TEXT NOT NULL,
    sgbd         TEXT NOT NULL,
    dbname       TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    finished_at  TEXT,
    status       TEXT NOT NULL,         -- running | success | error
    path         TEXT,
    raw_size     INTEGER,
    size         INTEGER,
    sha256       TEXT,
    compressed   INTEGER NOT NULL DEFAULT 0,
    encrypted    INTEGER NOT NULL DEFAULT 0,
    duration     REAL,
    error        TEXT,
    verified_at  TEXT,
    verify_ok    INTEGER,
    deleted_at   TEXT
);
CREATE INDEX IF NOT EXISTS ix_backups_created ON backups(created_at);
"""

_init_lock = threading.Lock()
_initialized = False


def now():
    return datetime.now().replace(microsecond=0)


def iso(dt):
    return dt.isoformat(sep=" ") if dt else None


def _connect():
    conn = sqlite3.connect(settings.DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init():
    global _initialized
    with _init_lock:
        if _initialized:
            return
        settings.ensure_dirs()
        with _connect() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(SCHEMA)
        _initialized = True


@contextmanager
def db():
    init()
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def rows(sql, args=()):
    with db() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def row(sql, args=()):
    with db() as c:
        r = c.execute(sql, args).fetchone()
        return dict(r) if r else None


def execute(sql, args=()):
    with db() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


# ------------------------------------------------------------------ settings

def get_setting(key, default=None):
    r = row("SELECT value FROM settings WHERE key=?", (key,))
    return json.loads(r["value"]) if r else default


def set_setting(key, value):
    execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(value)),
    )


# ------------------------------------------------------------------- users

def count_users():
    return row("SELECT COUNT(*) AS n FROM users")["n"]


def get_user(username):
    return row("SELECT * FROM users WHERE username=?", (username,))


def upsert_user(username, password_hash):
    execute(
        "INSERT INTO users(username, password_hash, created_at) VALUES(?, ?, ?) "
        "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash",
        (username, password_hash, iso(now())),
    )
