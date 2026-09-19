"""
Database Connection & Migration Manager for BRAHMO Clinical AI.
Runs numbered SQL migrations from migrations/ directory.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional
from src.core.config import config

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = db_path or config.db_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    # Enforce foreign key constraints and high-concurrency WAL mode
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def run_migrations(db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Track executed migrations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()

    # Find and sort migration files
    migration_files = sorted(config.migrations_dir.glob("*.sql"))
    for mig in migration_files:
        version_num = int(mig.name.split("_")[0])
        cursor.execute("SELECT version FROM schema_migrations WHERE version = ?", (version_num,))
        if cursor.fetchone() is None:
            print(f"Applying migration {mig.name}...")
            with open(mig, "r", encoding="utf-8") as f:
                sql_content = f.read()
            cursor.executescript(sql_content)
            cursor.execute(
                "INSERT INTO schema_migrations (version, filename) VALUES (?, ?)",
                (version_num, mig.name)
            )
            conn.commit()
            print(f"Migration {mig.name} applied successfully.")

    conn.close()

if __name__ == "__main__":
    run_migrations()
    print("All migrations up to date.")
