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
    
    # Store original document hashes to prevent rogue injection
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS document_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_hash TEXT,
        issued_to TEXT,
        role TEXT,
        department TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def register_document(document_hash: str, issued_to: str, role: str, department: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO document_registry (document_hash, issued_to, role, department)
    VALUES (?, ?, ?, ?)
    ''', (document_hash, issued_to, role, department))
    conn.commit()
    conn.close()

def check_document_registry(document_hash: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM document_registry WHERE document_hash = ?", (document_hash,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

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
