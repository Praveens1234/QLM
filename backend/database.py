import sqlite3
import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from backend.core.retry import db_retry

logger = logging.getLogger("QLM.Database")

class Database:
    """
    Centralized SQLite Database Manager.
    Handles connection pooling (basic), schema migration, and safe execution.
    Implements WAL mode for better concurrency and ACID compliance.
    Includes Automatic Retry for Locking Errors.
    """

    def __init__(self, db_path: str = "data/qlm.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_pragmas()
        self._init_schema()

    @db_retry
    def _init_pragmas(self):
        """
        Enable Write-Ahead Logging (WAL) and other performance settings.
        Wrapped in retry to handle initial lock contention.
        """
        try:
            with self.get_connection() as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA foreign_keys=ON;")
                conn.execute("PRAGMA busy_timeout=5000;") # 5 seconds
        except Exception as e:
            logger.error(f"Failed to set database pragmas: {e}")
            raise e

    @db_retry
    def _init_schema(self):
        """
        Initialize the database schema.
        Idempotent: Only creates tables if they don't exist.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # --- Config Table ---
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS config (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # --- Providers Table ---
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS providers (
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        base_url TEXT,
                        api_key TEXT,
                        models TEXT, -- JSON list of models
                        is_active BOOLEAN DEFAULT 0
                    )
                ''')

                # --- Jobs/Memory Table ---
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jobs (
                        session_id TEXT PRIMARY KEY,
                        goal TEXT,
                        status TEXT,
                        steps_completed TEXT, -- JSON list
                        artifacts TEXT, -- JSON dict
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # --- Chat Sessions ---
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # --- Chat Messages ---
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        session_id TEXT,
                        role TEXT,
                        content TEXT,
                        tool_calls TEXT,
                        tool_call_id TEXT,
                        name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                    )
                ''')

                # --- Datasets Metadata ---
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS datasets (
                        id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        detected_tf_sec INTEGER,
                        start_date TEXT,
                        end_date TEXT,
                        row_count INTEGER,
                        file_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # --- Audit Logs (New Phase Requirement) ---
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id TEXT PRIMARY KEY,
                        session_id TEXT,
                        action TEXT,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # --- Orders Table (Execution Persistence) ---
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        side TEXT NOT NULL,
                        type TEXT NOT NULL,
                        price REAL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        filled_at TIMESTAMP,
                        fill_price REAL,
                        commission REAL DEFAULT 0.0,
                        external_id TEXT
                    )
                ''')

                # --- Positions Table (Execution Persistence) ---
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS positions (
                        id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        entry_price REAL NOT NULL,
                        current_price REAL,
                        unrealized_pnl REAL DEFAULT 0.0,
                        realized_pnl REAL DEFAULT 0.0,
                        status TEXT NOT NULL, -- OPEN, CLOSED
                        opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        closed_at TIMESTAMP
                    )
                ''')

                conn.commit()
                logger.info(f"Database initialized at {self.db_path} (WAL Mode)")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise e

    @contextmanager
    def get_connection(self):
        """
        Yields a SQLite connection with a 10s timeout to handle concurrency.
        Ensures clean closing.
        """
        # Increased timeout to 10s to prevent 'database is locked' during heavy writes
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row # Return dict-like objects
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

# Singleton instance
db = Database()
