import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "pokenode.db")

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            coins INTEGER DEFAULT 0,
            trainer_level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            starter TEXT DEFAULT NULL,
            shiny_count INTEGER DEFAULT 0,
            last_checkin TEXT DEFAULT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS shinies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            username TEXT,
            pokemon TEXT,
            claimed_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            event_type TEXT,
            description TEXT,
            created_by TEXT,
            ends_at TEXT,
            active INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS event_participants (
            event_id INTEGER,
            user_id TEXT,
            username TEXT,
            PRIMARY KEY (event_id, user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offerer_id TEXT,
            offerer_name TEXT,
            target_id TEXT,
            offer TEXT,
            want TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized.")

init_db()