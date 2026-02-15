import sqlite3
import os
import json
from typing import List, Dict, Optional, Any

class MetadataStore:
    """
    Manages dataset metadata using SQLite.
    """
    
    def __init__(self, db_path: str = "data/metadata.db"):
        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
                created_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def add_dataset(self, metadata: Dict[str, Any]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO datasets (id, symbol, timeframe, detected_tf_sec, start_date, end_date, row_count, file_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata['id'],
            metadata['symbol'],
            metadata['timeframe'],
            metadata['detected_tf_sec'],
            metadata['start_date'],
            metadata['end_date'],
            metadata['row_count'],
            metadata['file_path'],
            metadata['created_at']
        ))
        
        conn.commit()
        conn.close()

    def list_datasets(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM datasets ORDER BY created_at DESC')
        rows = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM datasets WHERE id = ?', (dataset_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None

    def delete_dataset(self, dataset_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM datasets WHERE id = ?', (dataset_id,))
        
        conn.commit()
        conn.close()
