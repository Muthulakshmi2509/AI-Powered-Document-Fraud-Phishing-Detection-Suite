import sqlite3
import os

DB_PATH = "documents.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Logs for dashboard
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scan_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        extracted_data TEXT,
        score REAL,
        verdict TEXT,
        reasons TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Store image hashes to detect duplicates
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS image_hashes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        phash TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def log_scan(filename: str, extracted_data: str, score: float, verdict: str, reasons: list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    reasons_str = "; ".join(reasons)
    cursor.execute('''
    INSERT INTO scan_logs (filename, extracted_data, score, verdict, reasons)
    VALUES (?, ?, ?, ?, ?)
    ''', (filename, extracted_data, score, verdict, reasons_str))
    conn.commit()
    conn.close()
