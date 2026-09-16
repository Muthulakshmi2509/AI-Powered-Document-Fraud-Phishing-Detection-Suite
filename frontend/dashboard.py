import streamlit as st
import requests
import pandas as pd
import sqlite3
import os
import json
import pyotp
import base64
import hashlib

def get_user_secret(username: str) -> str:
    h = hashlib.sha256(username.strip().lower().encode('utf-8')).digest()
    return base64.b32encode(h).decode('utf-8')[:32]

import time

st.set_page_config(page_title="Document Verifier", layout="wide")

# --- MOCK AUTHENTICATOR APP ---
st.sidebar.title("📱 Setup Google Authenticator")

# Generate provisioning URI for Google Authenticator
totp = pyotp.TOTP("JBSWY3DPEHPK3PXP")
uri = totp.provisioning_uri(name='Employee@Company.com', issuer_name='DocVerifier Security')

import qrcode
from PIL import Image
import io

qr_img = qrcode.make(uri)
buf = io.BytesIO()
qr_img.save(buf, format="PNG")
st.sidebar.image(buf.getvalue(), caption="Scan with Google Authenticator")
st.sidebar.success("Once scanned, use the 6-digit code from your phone to seal documents!")

API_VERIFY_URL = "http://localhost:8000/api/verify"
API_SEAL_URL = "http://localhost:8000/api/seal"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "documents.db")

tab1, tab2, tab3 = st.tabs(["Verification Panel", "Database Overview", "Seal Document 🔐"])

with tab1:
    st.title("Document Verification")
    uploaded_file = st.file_uploader("Upload Document to Verify", type=["jpg", "jpeg", "png", "pdf", "docx", "csv", "txt"])
    
    if uploaded_file is not None:
        if st.button("Verify"):
            with st.spinner("Analyzing document..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                try:
                    response = requests.post(API_VERIFY_URL, files=files)
                    if response.status_code == 200:
                        result = response.json()
                        st.success("Analysis Complete!")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Extracted Data")
                            st.json(result.get("extracted_data", {}))
                            
                        with col2:
                            st.subheader("Risk Assessment")
                            verdict = result.get("verdict", "UNKNOWN")
                            if "HIGH" in verdict:
                                st.error(f"Verdict: {verdict}")
                            elif "MEDIUM" in verdict:
                                st.warning(f"Verdict: {verdict}")
                            else:
                                st.success(f"Verdict: {verdict}")
                                
                            st.metric("Risk Score", result.get("score", 0))
                            
                            st.write("### Reasons & Audit Log")
                            for reason in result.get("reasons", []):
                                st.write(f"- {reason}")
                    else:
                        st.error(f"Error from API: {response.text}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

with tab2:
    st.title("Database Overview")
    
    def load_data():
        try:
            if not os.path.exists(DB_PATH):
                return pd.DataFrame()
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("SELECT * FROM scan_logs ORDER BY timestamp DESC", conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error reading database: {e}")
            return pd.DataFrame()

    df = load_data()
    
    if not df.empty:
        total_docs = len(df)
        high_risk_count = len(df[df['verdict'] == 'HIGH RISK'])
        
        col1, col2, col3 = st.columns([2, 2, 1])
        col1.metric("Total Documents Scanned", total_docs)
        col2.metric("High Risk Documents", high_risk_count)
        
        with col3:
            st.write("") # spacer
            if st.button("🗑️ Clear History", use_container_width=True):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM scan_logs")
                    cursor.execute("DELETE FROM image_hashes")
                    conn.commit()
                    conn.close()
                    st.success("Database cleared!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error clearing db: {e}")
        
        st.subheader("Past Scans")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No scan logs found. Verify some documents first.")

with tab3:
    st.title("Cryptographic Document Sealer & Audit Trail 🔐")
    st.write("Upload an original, verified document to generate a hidden cryptographic signature (HMAC SHA-256) inside the file. By entering the employee details below, you establish a **Zero-Trust Chain of Custody**. If a bad actor modifies this sealed file later, the engine will instantly flag it as a Forgery and reveal exactly who was responsible for the document when the seal was broken.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        emp_name = st.text_input("Employee / Custodian Name", placeholder="e.g., John Doe")
    emp_role = st.selectbox("Role", ["Clerk", "Manager", "Finance Director", "External Auditor"])
    action = st.radio("Action", ["Originate Document (Initial Seal)", "Acknowledge Receipt (Transfer Custody)", "Approve Document"])
    # mapping actions to short codes
    
    st.info("Because every employee has a unique MFA key, type your name above to generate your specific QR code!")
    current_name = emp_name if emp_name else "Unknown"
    user_secret = get_user_secret(current_name)
    totp = pyotp.TOTP(user_secret)
    uri = totp.provisioning_uri(name=f'{current_name}@Company.com', issuer_name='DocVerifier Security')
      
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    img_byte_arr = io.BytesIO()
    img_qr.save(img_byte_arr, format='PNG')
    st.image(img_byte_arr, caption=f"MFA QR Code for {current_name}", width=200)

    action_code = "SEALED"
    if "Receipt" in action: action_code = "RECEIVED"
    if "Approve" in action: action_code = "APPROVED"
    with col2:
        dept_name = st.text_input("Department", placeholder="e.g., Finance")
    with col3:
        mfa_token = st.text_input("Hardware Key / MFA PIN 🔑", placeholder="Enter 6-digit code", type="password")
        
    seal_file = st.file_uploader("Upload Original Document", type=["jpg", "jpeg", "png", "pdf", "docx", "csv", "txt"], key="sealer")
    
    if seal_file is not None:
        if st.button("Generate Sealed Document & Assign Custody"):
            if not mfa_token:
                st.error("Authentication Failed: You must provide a valid Hardware Key or MFA PIN to sign this document.")
            else:
                with st.spinner("Injecting cryptographic seal and audit trail..."):
                    files = {"file": (seal_file.name, seal_file.getvalue(), seal_file.type)}
                    data = {
                        "employee_name": emp_name if emp_name else "Unknown",
                        "employee_role": emp_role,
                        "department": dept_name if dept_name else "Unknown",
                        "mfa_token": mfa_token,
                        "action": action_code
                    }
                try:
                    response = requests.post(API_SEAL_URL, files=files, data=data)
                    if response.status_code == 200:
                        st.success(f"Document Cryptographically Sealed and entrusted to {emp_name if emp_name else 'Unknown'}!")
                        
                        st.download_button(
                            label="Download Sealed Document",
                            data=response.content,
                            file_name=f"SEALED_{seal_file.name}",
                            mime=seal_file.type
                        )
                    else:
                        st.error(f"Error sealing document: {response.text}")
                except Exception as e:
                    st.error(f"Connection error: {e}")
