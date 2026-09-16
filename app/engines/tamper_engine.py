import io
import os
import cv2
import numpy as np
from PIL import Image, ExifTags, ImageChops

def analyze_exif(img):
    reasons = []
    penalty = 0.0
    
    try:
        exif_data = img._getexif() if hasattr(img, '_getexif') else None
        
        if not exif_data:
            reasons.append("No EXIF metadata found (could be stripped or native digital).")
            penalty += 10.0
            return penalty, reasons, {}
            
        exif = {
            ExifTags.TAGS.get(k, k): v
            for k, v in exif_data.items()
        }
        
        # Clean up binary/non-string metadata for JSON serialization
        clean_exif = {}
        for k, v in exif.items():
            if isinstance(v, (bytes, bytearray)):
                try:
                    clean_exif[k] = v.decode('utf-8', errors='ignore')
                except:
                    clean_exif[k] = "<binary data>"
            else:
                clean_exif[k] = str(v)
        
        # Check for software signatures
        software = clean_exif.get('Software', '').lower()
        suspicious_software = ['photoshop', 'gimp', 'lightroom', 'canva', 'illustrator']
        if any(susp_soft in software for susp_soft in suspicious_software):
            reasons.append(f"Suspicious software signature found in EXIF: {software}")
            penalty += 30.0
            
        # Inject metadata into reasons log instead of penalizing missing dates
        if clean_exif:
            important_keys = ['DateTimeOriginal', 'DateTime', 'Software', 'Make', 'Model', 'ImageWidth', 'ImageLength']
            meta_parts = []
            
            # First add the important ones if they exist
            for key in important_keys:
                if key in clean_exif:
                    meta_parts.append(f"{key}: {clean_exif[key]}")
                    
            # Then add a few others if we don't have many
            for k, v in clean_exif.items():
                if k not in important_keys and len(meta_parts) < 6:
                    meta_parts.append(f"{k}: {v}")
                    
            meta_str = " | ".join(meta_parts)
            if len(clean_exif) > len(meta_parts):
                meta_str += " | (and more...)"
                
            reasons.append(f"📄 Document EXIF Metadata: {meta_str}")
            
    except Exception as e:
        reasons.append(f"Error reading EXIF data: {str(e)}")
        penalty += 5.0
        
    return penalty, reasons, clean_exif

def analyze_ela(img):
    reasons = []
    penalty = 0.0
    
    try:
        # We need to save to a bytes buffer to simulate JPEG compression loss
        buffer = io.BytesIO()
        # Ensure image is in RGB before saving as JPEG
        original = img.convert('RGB')
        original.save(buffer, 'JPEG', quality=90)
        buffer.seek(0)
        
        resaved = Image.open(buffer)
        
        # Get absolute difference
        diff = ImageChops.difference(original, resaved)
        extrema = diff.getextrema()
        
        max_diff = max([ex[1] for ex in extrema]) if extrema else 0
        
        if max_diff == 0:
            max_diff = 1
            
        scale = 255.0 / max_diff
        
        ela_img = Image.eval(diff, lambda x: x * scale)
        
        # Convert to cv2 format to calculate standard deviation
        ela_cv = cv2.cvtColor(np.array(ela_img), cv2.COLOR_RGB2GRAY)
        
        mean_val, std_val = cv2.meanStdDev(ela_cv)
        
        if std_val[0][0] > 40.0:
            reasons.append(f"High variance in Error Level Analysis (std={std_val[0][0]:.2f}), suggesting potential manipulation.")
            penalty += 20.0
            
    except Exception as e:
        reasons.append(f"Error performing ELA analysis: {str(e)}")
        
    return penalty, reasons

def detect_tampering(image_bytes: bytes):
    total_penalty = 0.0
    all_reasons = []
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # EXIF Analysis
        exif_penalty, exif_reasons, metadata = analyze_exif(img)
        total_penalty += exif_penalty
        all_reasons.extend(exif_reasons)
        
        # ELA Analysis
        ela_penalty, ela_reasons = analyze_ela(img)
        total_penalty += ela_penalty
        all_reasons.extend(ela_reasons)
        
    except Exception as e:
        all_reasons.append(f"Failed to load image for tampering detection: {str(e)}")
        total_penalty += 100.0
    
    return min(total_penalty, 100.0), all_reasons, metadata
