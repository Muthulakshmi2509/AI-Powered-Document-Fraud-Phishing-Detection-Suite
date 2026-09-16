import hashlib
import hmac
import io
import qrcode
import cv2
import numpy as np
from PIL import Image
from datetime import datetime
from app.database import register_document, check_document_registry

SECRET_KEY = b"intelligent_doc_verifier_hackathon_key"
MARKER = b"||VERIFIER_SEAL||"

def seal_document(file_bytes: bytes, employee_name: str = "Unknown", department: str = "Unknown", client_ip: str = "Unknown IP", mfa_token: str = "NO_MFA", role: str = "Unknown", action: str = "SEALED") -> bytes:
    """
    Creates a cryptographic HMAC signature and embeds a Chain of Custody payload.
    The payload is injected invisibly into the EOF bytes.
    If the document has no prior seals, its hash is registered in the database.
    """
    signature = hmac.new(SECRET_KEY, file_bytes, hashlib.sha256).hexdigest()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Register in DB if it's the original (no seals yet)
    if MARKER not in file_bytes:
        base_hash = hashlib.sha256(file_bytes).hexdigest()
        register_document(base_hash, employee_name, role, department)
        
    payload = f"SEAL:{signature}|ACTION:{action}|ISSUED_TO:{employee_name}|ROLE:{role}|DEPT:{department}|TIME:{timestamp}|IP:{client_ip}|MFA:{mfa_token}"
        
    return file_bytes + MARKER + payload.encode('utf-8')

def check_seal(file_bytes: bytes):
    if MARKER not in file_bytes:
        return "UNSEALED", file_bytes, ["No cryptographic seal found on this document."]
        
    parts = file_bytes.split(MARKER)
    original_bytes = parts[0]
    
    base_hash = hashlib.sha256(original_bytes).hexdigest()
    is_registered = check_document_registry(base_hash)
    
    messages = []
    if is_registered:
        messages.append(f"🟢 **Document Registry:** Base document hash ({base_hash[:8]}...) found in secure registry.")
    else:
        messages.append(f"🔴 **Document Registry Alert:** Base document hash is MISSING from the secure registry! This is likely a rogue document.")
        
    current_bytes = original_bytes
    seal_status = "AUTHENTIC"
    
    for i, payload_bytes in enumerate(parts[1:]):
        payload = payload_bytes.decode('utf-8', errors='ignore')
        
        # We will parse it first to get the last point of contact
        fields = payload.split('|')
        issued_to, role, dept, action = "Unknown", "Unknown", "Unknown", "SEALED"
        for p in fields:
            if p.startswith("ISSUED_TO:"): issued_to = p.split(":", 1)[1]
            if p.startswith("ROLE:"): role = p.split(":", 1)[1]
            if p.startswith("DEPT:"): dept = p.split(":", 1)[1]
            if p.startswith("ACTION:"): action = p.split(":", 1)[1]
            
        # STRICT TAMPER CHECK
        if len(payload_bytes) > 500 or b'%%EOF' in payload_bytes or b'\x00' in payload_bytes:
            messages.append(f"🔴 **Seal {i+1} BROKEN:** Unauthorized data was appended after the seal! (Last point of contact before tampering: **{issued_to}** [{role}])")
            seal_status = "BROKEN"
            break
        
        try:
            fields = payload.split('|')
            claimed_signature = fields[0].replace("SEAL:", "")
            issued_to, role, dept, time, ip_addr = "Unknown", "Unknown", "Unknown", "Unknown", "Unknown IP"
            mfa_verified = False
            
            for p in fields[1:]:
                if p.startswith("ISSUED_TO:"): issued_to = p.split(":", 1)[1]
                if p.startswith("ROLE:"): role = p.split(":", 1)[1]
                if p.startswith("DEPT:"): dept = p.split(":", 1)[1]
                if p.startswith("TIME:"): time = p.split(":", 1)[1]
                if p.startswith("IP:"): ip_addr = p.split(":", 1)[1]
                if p.startswith("MFA:") and p.split(":", 1)[1] != "NO_MFA": mfa_verified = True
                
            expected_signature = hmac.new(SECRET_KEY, current_bytes, hashlib.sha256).hexdigest()
            mfa_msg = "📱 (MFA Authenticated)" if mfa_verified else "⚠️ (No MFA)"
            
            if hmac.compare_digest(expected_signature, claimed_signature):
                messages.append(f"🟢 **Seal {i+1} Valid [{action}]:** Entrusted to {issued_to} ({role} - {dept}) on {time}. {mfa_msg}")
            else:
                messages.append(f"🔴 **Seal {i+1} BROKEN:** Entrusted to {issued_to} ({role} - {dept}) on {time}. The chain of custody was altered before this seal!")
                seal_status = "BROKEN"
                
        except Exception:
            messages.append(f"🔴 **Seal {i+1} BROKEN:** Invalid or corrupted seal format detected!")
            seal_status = "BROKEN"
            
        current_bytes = current_bytes + MARKER + payload_bytes
        
    if not is_registered:
        seal_status = "BROKEN"
        
    return seal_status, original_bytes, messages
