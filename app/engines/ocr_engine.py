import easyocr
import re
from .text_engine import parse_text

# Initialize the EasyOCR reader
reader = easyocr.Reader(['en'], gpu=False)

def extract_data(image_bytes: bytes):
    """
    Extracts text from image bytes via EasyOCR, then uses AI NLP to parse fields.
    Returns: (extracted_data, ocr_score, ocr_reasons)
    """
    results = reader.readtext(image_bytes, detail=1)
    
    raw_text = " ".join([res[1] for res in results])
    confidences = [res[2] for res in results]
    
    ocr_score = 0
    ocr_reasons = []
    
    # --- TYPOGRAPHY & FONT ANOMALY DETECTION ---
    # Calculate the heights of all bounding boxes (res[0] is the bbox: [top_left, top_right, bottom_right, bottom_left])
    # Height = bottom_left_y - top_left_y
    heights = []
    for res in results:
        bbox = res[0]
        try:
            h = bbox[3][1] - bbox[0][1]
            heights.append(h)
        except:
            pass
            
    if len(heights) > 5:
        avg_height = sum(heights) / len(heights)
        # Find extreme outliers (e.g. someone pasted a giant or tiny number)
        outliers = [h for h in heights if h > avg_height * 1.8 or h < avg_height * 0.4]
        if outliers:
            ocr_score += 25
            ocr_reasons.append(f"👁️ Typography Anomaly: Detected {len(outliers)} text regions with highly irregular font sizes/kerning compared to the document average. Possible spliced text manipulation.")
            
    # Evaluate OCR quality penalty
    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        if avg_conf < 0.6:
            ocr_score += 30
            ocr_reasons.append(f"Low overall OCR confidence: {avg_conf:.2f}")
    else:
        ocr_score += 50
        ocr_reasons.append("No text could be extracted from the image.")
        
    # Defer to AI NLP engine to actually pull out the structured fields
    extracted_data, parse_score, parse_reasons = parse_text(raw_text)
    
    total_score = min(ocr_score + parse_score, 100)
    all_reasons = ocr_reasons + parse_reasons
    
    return extracted_data, total_score, all_reasons
