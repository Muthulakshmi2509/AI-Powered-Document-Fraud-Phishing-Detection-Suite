import hashlib
import hmac
import io
import qrcode
import cv2
import numpy as np
from PIL import Image
from datetime import datetime

SECRET_KEY = b"intelligent_doc_verifier_hackathon_key"
MARKER = b"||VERIFIER_SEAL||"

def seal_document(file_bytes: bytes, employee_name: str = "Unknown", department: str = "Unknown", client_ip: str = "Unknown IP", mfa_token: str = "NO_MFA") -> bytes:
    """
    Creates a cryptographic HMAC signature and embeds a Chain of Custody payload.
    The payload is injected invisibly into the EOF bytes.
    """
    signature = hmac.new(SECRET_KEY, file_bytes, hashlib.sha256).hexdigest()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    payload = f"SEAL:{signature}|ISSUED_TO:{employee_name}|DEPT:{department}|TIME:{timestamp}|IP:{client_ip}|MFA:{mfa_token}"
        
    return file_bytes + MARKER + payload.encode('utf-8')

def check_seal(file_bytes: bytes):
    payload = None
    original_bytes = file_bytes
    
    # 1. Check EOF Marker
    if MARKER in file_bytes:
        parts = file_bytes.rsplit(MARKER, 1)
        original_bytes = parts[0]
        payload = parts[1].decode('utf-8', errors='ignore')

    if not payload:
        return "UNSEALED", file_bytes, "No cryptographic seal found on this document."

    # Parse Payload
    try:
        parts = payload.split('|')
        claimed_signature = parts[0].replace("SEAL:", "")
        issued_to = "Unknown"
        dept = "Unknown"
        time = "Unknown"
        ip_addr = "Unknown IP"
        mfa_verified = False
        
        for p in parts[1:]:
            if p.startswith("ISSUED_TO:"): issued_to = p.split(":", 1)[1]
            if p.startswith("DEPT:"): dept = p.split(":", 1)[1]
            if p.startswith("TIME:"): time = p.split(":", 1)[1]
            if p.startswith("IP:"): ip_addr = p.split(":", 1)[1]
            if p.startswith("MFA:") and p.split(":", 1)[1] != "NO_MFA": mfa_verified = True
            
        expected_signature = hmac.new(SECRET_KEY, original_bytes, hashlib.sha256).hexdigest()
        
        mfa_msg = "✅ (MFA Authenticated)" if mfa_verified else "⚠️ (No MFA)"
        
        if hmac.compare_digest(expected_signature, claimed_signature):
            return "AUTHENTIC", original_bytes, f"🔏 Cryptographic Seal Valid! Chain of Custody intact. Document was safely entrusted to **{issued_to} ({dept})** on {time}. (Sealed by IP: {ip_addr}) {mfa_msg}"
        else:
            return "BROKEN", original_bytes, f"🚨 Chain of Custody Alert! Document was cryptographically sealed and entrusted to **{issued_to} ({dept})** on {time} (Sealed by IP: {ip_addr}) {mfa_msg}. It has been secretly altered AFTER this handover!"
    except Exception:
        return "BROKEN", original_bytes, "🚨 Invalid or corrupted seal format detected!"
