import os
import io
import sqlite3
import imagehash
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'documents.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_hashes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            phash TEXT
        )
    ''')
    conn.commit()
    conn.close()

def generate_phash(image_bytes: bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return str(imagehash.phash(img))
    except Exception:
        return None

def check_duplicate(image_bytes: bytes):
    init_db()
    reasons = []
    penalty = 0.0
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        new_hash = imagehash.phash(img)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT filename, phash FROM image_hashes")
        rows = cursor.fetchall()
        conn.close()
        
        duplicate_found = False
        duplicate_doc = None
        min_dist = float('inf')
        
        for filename, db_hash_str in rows:
            db_hash = imagehash.hex_to_hash(db_hash_str)
            distance = new_hash - db_hash
            if distance <= 3:
                duplicate_found = True
                duplicate_doc = filename
                if distance < min_dist:
                    min_dist = distance
                
        if duplicate_found:
            reasons.append(f"Duplicate image detected! Matches existing document {duplicate_doc} with a hamming distance of {min_dist}.")
            penalty = 100.0 
            
    except Exception as e:
        reasons.append(f"Error checking for duplicates: {str(e)}")
        
    return penalty, reasons

def save_hash(filename: str, phash_str: str):
    if not phash_str:
        return
        
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO image_hashes (filename, phash) VALUES (?, ?)", (filename, phash_str))
    conn.commit()
    conn.close()

import json

def check_fraud_ring(extracted_data: dict) -> tuple[int, list]:
    """
    Cross-references extracted entities (Names, Orgs) against past high-risk documents 
    to detect organized fraud rings.
    """
    penalty = 0
    reasons = []
    
    names = extracted_data.get('names', [])
    orgs = extracted_data.get('organizations', [])
    
    if not names and not orgs:
        return penalty, reasons
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Look for past documents that were flagged as HIGH RISK
        cursor.execute("SELECT extracted_data FROM scan_logs WHERE verdict = 'HIGH RISK'")
        rows = cursor.fetchall()
        
        for row in rows:
            try:
                past_data = json.loads(row[0])
                past_names = past_data.get('names', [])
                past_orgs = past_data.get('organizations', [])
                
                # Check for overlap
                shared_names = set(names).intersection(set(past_names))
                shared_orgs = set(orgs).intersection(set(past_orgs))
                
                if shared_names or shared_orgs:
                    shared = list(shared_names) + list(shared_orgs)
                    reasons.append(f"🕸️ Fraud Ring Alert: The entities {shared} were found in a previously flagged HIGH RISK document! Systemic fraud suspected.")
                    penalty += 50
                    break # Stop after finding one major link
            except:
                continue
                
        conn.close()
    except Exception as e:
        pass
        
    return penalty, reasons
