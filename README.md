# 🛡️ Intelligent Document Verifier & Fraud Detection Suite

![Python](https://img.shields.io/badge/Python-3.13-blue.svg) ![FastAPI](https://img.shields.io/badge/FastAPI-0.103-green.svg) ![Streamlit](https://img.shields.io/badge/Streamlit-1.27-red.svg) ![Machine Learning](https://img.shields.io/badge/AI%2FML-Random%20Forest-orange.svg)

An enterprise-grade, Zero-Trust document security platform designed to detect Insider Threat fraud, forged invoices, and maliciously altered documents.

---

## 🚨 The Problem: Encryption is Not Enough
Standard encryption (PGP/HTTPS) protects a document *in transit*. However, once an authorized employee decrypts a file, encryption's job is over. That employee can easily open the decrypted document in Photoshop, alter a financial amount, and commit fraud (Insider Threat). 

## 💡 Our Solution: Endpoint Integrity & AI Forensics
This platform shifts security from the network to the document itself. By using steganographic sealing, strict Multi-Factor Authentication (MFA), and deep Machine Learning forensics, we prove mathematically and visually whether a document has been forged, even if it was altered by an authorized user.

---

## 🌟 Key Hackathon Novelty Features

### 1. 🔏 Zero-Trust Chain of Custody (Steganographic Sealing)
When a document is finalized, an authorized user must input a live **Google Authenticator (TOTP) MFA PIN**. The system generates a cryptographic HMAC SHA-256 signature and permanently fuses it—along with the employee's Name, Department, IP Address, and Timestamp—invisibly into the file's End-Of-File (EOF) binary bytes.
* **Result:** If a single pixel is altered later, the seal breaks and loudly exposes exactly which employee/IP address handled it last.

### 2. 👁️ AI Typography & Computer Vision Anomaly Detection
Fraudsters rarely match the exact sub-pixel font rendering of an original document. Our OCR engine mathematically calculates the bounding box heights of all text on the page. If a spliced number (e.g., adding a `0` to make `$50` into `$500`) is statistically larger or smaller than the document's average font kerning, the AI flags a **Typography Anomaly**.

### 3. 🧠 Logical Math Hallucination Check
Fraudsters often change the "Total" amount on an invoice but forget to mathematically recalculate the "Subtotal" and "Tax" lines. Our heuristic engine extracts all monetary amounts and verifies if the smaller numbers logically roll up into the claimed total, catching human math errors in forgeries.

### 4. 🌍 Geospatial EXIF Mismatch 
The AI NLP engine (SpaCy) extracts geographical locations (e.g., "New York, NY") from the raw text. It then cross-references this against the document's hidden EXIF GPS coordinates. If an invoice claims to be from a local supplier but the photo was taken in a foreign timezone, it flags a **Geospatial Spoofing Anomaly**.

### 5. 🕸️ Systemic Fraud Ring Detection (Knowledge Graph)
Fraud is rarely a one-time event. When a document is scanned, our engine cross-references the extracted Entities (Names, Organizations) against a SQLite database of historically forged documents. If a newly submitted invoice shares an organization name with a previously flagged high-risk document, it triggers a systemic **Fraud Ring Alert**.

---

## 🛠️ Tech Stack
* **Backend:** FastAPI (Python)
* **Frontend:** Streamlit
* **AI & NLP:** SpaCy (Named Entity Recognition), Scikit-Learn (Random Forest)
* **Computer Vision:** OpenCV (Error Level Analysis), EasyOCR
* **Cryptography:** `hmac`, `hashlib`, `pyotp` (Time-Based One-Time Passwords)
* **Database:** SQLite

---

## 🚀 Installation & Running

**1. Install Dependencies**
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

**2. Start the Backend API (FastAPI)**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**3. Start the Frontend Dashboard (Streamlit)**
Open a new terminal and run:
```bash
python -m streamlit run frontend/dashboard.py
```

Open `http://localhost:8501` in your browser. Scan the QR code on the sidebar with Google Authenticator to begin testing the Zero-Trust MFA Sealer!
