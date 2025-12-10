"""
Database connection helpers for DF Tales.
"""

import sqlite3
from pathlib import Path
from flask import g

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MASTER_DB_PATH = DATA_DIR / "master.db"
MASTER_SCHEMA_PATH = BASE_DIR / "master_schema.sql"


def get_master_db():
    """Get master database connection."""
    if 'master_db' not in g:
        DATA_DIR.mkdir(exist_ok=True)
        g.master_db = sqlite3.connect(MASTER_DB_PATH)
        g.master_db.row_factory = sqlite3.Row
        # Initialize schema if needed
        with open(MASTER_SCHEMA_PATH) as f:
            g.master_db.executescript(f.read())
        # Migration: add has_plus and has_map columns if they don't exist
        cursor = g.master_db.cursor()
        cursor.execute("PRAGMA table_info(worlds)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'has_plus' not in columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN has_plus INTEGER DEFAULT 0")
            g.master_db.commit()
        if 'has_map' not in columns:
            cursor.execute("ALTER TABLE worlds ADD COLUMN has_map INTEGER DEFAULT 0")
            g.master_db.commit()
    return g.master_db


def get_current_world():
    """Get the current active world from master database."""
    db = get_master_db()
    row = db.execute("SELECT * FROM worlds WHERE is_current = 1").fetchone()
    return dict(row) if row else None


def get_all_worlds():
    """Get all available worlds from master database."""
    db = get_master_db()
    rows = db.execute("SELECT * FROM worlds ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def get_db():
    """Get database connection for current world."""
    if 'db' not in g:
        world = get_current_world()
        if world and Path(world['db_path']).exists():
            g.db = sqlite3.connect(world['db_path'])
            g.db.row_factory = sqlite3.Row
        else:
            g.db = None
    return g.db


def close_db(error=None):
    """Close database connections at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
    master_db = g.pop('master_db', None)
    if master_db is not None:
        master_db.close()


def get_stats():
    """Get database statistics."""
    db = get_db()
    if not db:
        return None

    stats = {}
    tables = [
        ('regions', 'Regions'),
        ('sites', 'Sites'),
        ('historical_figures', 'Historical Figures'),
        ('entities', 'Entities'),
        ('artifacts', 'Artifacts'),
        ('historical_events', 'Events'),
        ('written_content', 'Written Works'),
    ]

    for table, label in tables:
        try:
            count = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            stats[label] = count
        except:
            stats[label] = 0

    return stats


def get_world_info():
    """Get world name and altname."""
    db = get_db()
    if not db:
        return None

    try:
        row = db.execute("SELECT name, altname FROM world LIMIT 1").fetchone()
        if row:
            return {'name': row['name'], 'altname': row['altname']}
    except:
        pass
    return None


def get_current_year():
    """Get the current year of the world."""
    db = get_db()
    if not db:
        return None
    try:
        row = db.execute("SELECT MAX(MAX(birth_year), MAX(death_year)) as year FROM historical_figures WHERE death_year != -1").fetchone()
        return row['year'] if row else None
    except:
        return None
