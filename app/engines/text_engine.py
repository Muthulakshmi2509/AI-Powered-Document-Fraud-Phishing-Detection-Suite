import re
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = None

def parse_text(raw_text: str):
    """
    Parses structured fields from raw text using AI-based Named Entity Recognition (NER)
    and robust Regex fallbacks.
    Returns: (extracted_data, score, reasons)
    """
    score = 0
    reasons = []
    
    if not raw_text.strip():
        score += 50
        reasons.append("No text could be extracted from the document.")
        
    dates_found = []
    amounts_found = []
    names_found = []
    orgs_found = []
    locations_found = []
    
    # 1. AI-Based NLP Extraction (SpaCy NER)
    if nlp is not None:
        doc = nlp(raw_text)
        for ent in doc.ents:
            if ent.label_ == "DATE":
                dates_found.append(ent.text)
            elif ent.label_ == "PERSON":
                names_found.append(ent.text)
            elif ent.label_ == "ORG":
                orgs_found.append(ent.text)
            elif ent.label_ == "GPE" or ent.label_ == "LOC":
                locations_found.append(ent.text)
            elif ent.label_ == "MONEY":
                try:
                    num = float(re.sub(r'[^\d.]', '', ent.text))
                    amounts_found.append(num)
                except ValueError:
                    pass
                    
    # 2. Regex Fallbacks for structured fields not caught by AI
    date_pattern = r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b'
    amount_pattern = r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b'
    
    regex_dates = re.findall(date_pattern, raw_text)
    for rd in regex_dates:
        if rd not in dates_found:
            dates_found.append(rd)
            
    regex_amounts = re.findall(amount_pattern, raw_text)
    for ra in regex_amounts:
        try:
            val = float(ra.replace(',', ''))
            if val not in amounts_found:
                amounts_found.append(val)
        except ValueError:
            pass
            
    extracted_data = {
        'organizations': list(set(orgs_found)),
        'dates': list(set(dates_found)),
        'amounts': list(set(amounts_found)),
        'names': list(set(names_found)),
        'locations': list(set(locations_found)),
        'raw_text': raw_text
    }
    
    return extracted_data, min(score, 100), reasons
