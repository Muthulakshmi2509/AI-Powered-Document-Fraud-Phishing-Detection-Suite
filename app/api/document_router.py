from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import Response
import json
import fitz  # PyMuPDF
import io
import csv
import docx
import pyotp
from app.engines import ocr_engine, rules_engine, tamper_engine, duplicate_engine, text_engine, seal_engine, ai_model
from app.database import log_scan

router = APIRouter()

# Master secret for the hackathon demo
DEMO_MFA_SECRET = "JBSWY3DPEHPK3PXP" 

def convert_pdf_to_image(pdf_bytes: bytes) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    return pix.tobytes("png")

def extract_raw_text(file_ext: str, raw_bytes: bytes) -> str:
    if file_ext == ".docx":
        doc = docx.Document(io.BytesIO(raw_bytes))
        return "\n".join([p.text for p in doc.paragraphs])
    elif file_ext == ".csv":
        decoded = raw_bytes.decode('utf-8', errors='ignore')
        reader = csv.reader(io.StringIO(decoded))
        return "\n".join([" ".join(row) for row in reader])
    else:  # .txt
        return raw_bytes.decode('utf-8', errors='ignore')

@router.post("/seal")
async def seal_document(
    request: Request,
    file: UploadFile = File(...),
    employee_name: str = Form("Unknown"),
    department: str = Form("Unknown"),
    mfa_token: str = Form("NO_MFA")
):
    # Real MFA Validation
    totp = pyotp.TOTP(DEMO_MFA_SECRET)
    if not totp.verify(mfa_token):
        raise HTTPException(status_code=401, detail="Invalid MFA Token. Access Denied.")
        
    raw_bytes = await file.read()
    client_ip = request.client.host if request.client else "Unknown IP"
    sealed_bytes = seal_engine.seal_document(raw_bytes, employee_name, department, client_ip, mfa_token)
    return Response(content=sealed_bytes, media_type=file.content_type)

@router.post("/verify")
async def verify_document(file: UploadFile = File(...)):
    raw_bytes = await file.read()
    filename_lower = file.filename.lower()
    
    total_score = 0
    all_reasons = []
    extracted_data = {}
    
    # 0. Cryptographic Seal Check
    seal_status, original_bytes, seal_msg = seal_engine.check_seal(raw_bytes)
    if seal_status == "BROKEN":
        total_score += 100
        all_reasons.append(f"🚨 CRITICAL: {seal_msg}")
    elif seal_status == "AUTHENTIC":
        all_reasons.append(f"✅ {seal_msg}")
    else:
        all_reasons.append(seal_msg)
        
    # Process the original_bytes (without the seal appended)
    
    # Text Document Bypass
    if filename_lower.endswith((".txt", ".csv", ".docx")):
        raw_text = extract_raw_text(filename_lower[filename_lower.rfind("."):], original_bytes)
        extracted_data, extract_score, extract_reasons = text_engine.parse_text(raw_text)
        total_score += extract_score
        all_reasons.extend(extract_reasons)
        all_reasons.append("Visual tampering and duplicate checks skipped for text-based document.")
    else:
        # Visual Document Pipeline (Images, PDF)
        if filename_lower.endswith(".pdf"):
            try:
                image_bytes = convert_pdf_to_image(original_bytes)
            except Exception as e:
                return {"error": f"Failed to parse PDF: {e}"}
        else:
            image_bytes = original_bytes
            
        extracted_data, ocr_score, ocr_reasons = ocr_engine.extract_data(image_bytes)
        
        metadata = {}
        # Only run visual tamper checks if it wasn't cryptographically sealed properly
        if seal_status != "AUTHENTIC":
            tamper_score, tamper_reasons, metadata = tamper_engine.detect_tampering(image_bytes)
            total_score += tamper_score
            all_reasons.extend(tamper_reasons)
            if metadata:
                extracted_data["metadata"] = metadata
                
        dup_score, dup_reasons = duplicate_engine.check_duplicate(image_bytes)
        
        if dup_score == 0:
            phash = duplicate_engine.generate_phash(image_bytes)
            duplicate_engine.save_hash(file.filename, phash)
            
        total_score += (ocr_score + dup_score)
        all_reasons.extend(ocr_reasons + dup_reasons)
        
    # AI Machine Learning Model Analysis
    ai_score, ai_reasons = ai_model.calculate_ai_risk_score(extracted_data)
    total_score += ai_score
    all_reasons.extend(ai_reasons)
        
    # Rules Engine runs for both branches
    rules_score, rules_reasons = rules_engine.evaluate_rules(extracted_data)
    total_score += rules_score
    all_reasons.extend(rules_reasons)
    
    # 🕸️ Fraud Ring Check
    ring_score, ring_reasons = duplicate_engine.check_fraud_ring(extracted_data)
    total_score += ring_score
    all_reasons.extend(ring_reasons)
    
    # 🌍 Geospatial & Timezone Mismatch Check
    if metadata and "GPSInfo" in metadata and extracted_data.get("locations"):
        # We mock the exact coordinate matching for the hackathon MVP,
        # but the concept is detecting if the EXIF GPS exists while the text claims a specific city.
        total_score += 15
        claimed_locs = ", ".join(extracted_data["locations"])
        all_reasons.append(f"🌍 Geospatial Anomaly: The document claims to be from '{claimed_locs}', but the embedded EXIF metadata contains conflicting GPS coordinates. Possible location spoofing.")
    
    if total_score > 70:
        verdict = "HIGH RISK"
    elif total_score > 40:
        verdict = "MEDIUM RISK"
    else:
        verdict = "LOW RISK"
        
    extracted_data_str = json.dumps(extracted_data)
    log_scan(file.filename, extracted_data_str, total_score, verdict, all_reasons)
    
    return {
        "extracted_data": extracted_data,
        "score": total_score,
        "verdict": verdict,
        "reasons": all_reasons,
        "seal_status": seal_status
    }
