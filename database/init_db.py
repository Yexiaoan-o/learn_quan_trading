import sqlite3
import os
import time
from config import DB_PATH


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id TEXT NOT NULL,
            section_id TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            score REAL DEFAULT 0,
            last_accessed TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(chapter_id, section_id)
        );

        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id TEXT NOT NULL,
            exercise_id TEXT NOT NULL,
            user_answer TEXT,
            correct INTEGER DEFAULT 0,
            score REAL DEFAULT 0,
            attempts INTEGER DEFAULT 1,
            completed_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(chapter_id, exercise_id)
        );

        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id TEXT NOT NULL,
            section_id TEXT,
            content TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id TEXT NOT NULL,
            section_id TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(chapter_id, section_id)
        );

        CREATE TABLE IF NOT EXISTS learning_time (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_id TEXT NOT NULL,
            date TEXT DEFAULT (date('now','localtime')),
            seconds INTEGER DEFAULT 0,
            UNIQUE(chapter_id, date)
        );
    """)
    conn.commit()
    conn.close()
    print(f"[DB] Database initialized at {DB_PATH}")


def dict_from_row(row):
    return dict(row) if row else None
