import sqlite3
import os
import json
from typing import List, Dict, Optional, Any
from backend.database import db

class MetadataStore:
    """
    Manages dataset metadata using the central SQLite DB.
    """
    
    def __init__(self):
        pass

    def add_dataset(self, metadata: Dict[str, Any]):
        with db.get_connection() as conn:
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

    def list_datasets(self) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM datasets ORDER BY created_at DESC')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM datasets WHERE id = ?', (dataset_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_dataset(self, dataset_id: str):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM datasets WHERE id = ?', (dataset_id,))
            conn.commit()
