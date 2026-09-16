from datetime import datetime

def evaluate_rules(extracted_data: dict):
    """
    Checks for inconsistencies in the extracted structured data.
    Returns: (rules_score, rules_reasons)
    """
    rules_reasons = []
    rules_score = 0
    
    dates = extracted_data.get('dates', [])
    amounts = extracted_data.get('amounts', [])
    
    # Removed Missing Required Fields check to support non-financial/general documents
    # 2. Date Validation
    # (Since we now use AI NLP, dates might be just years like '2025' or 'next week'.
    #  We skip the strict strptime formatting penalties to avoid false positives.)
    pass
            
    # 2. Financial Logic Anomaly (Math Hallucination Check)
    if len(amounts) >= 3:
        # Sort amounts to find potential subtotal, tax, and total
        sorted_amts = sorted(amounts)
        total_claimed = sorted_amts[-1]
        
        # See if any combination of the smaller amounts equals the total
        # (This catches forged totals where they forgot to edit the tax/subtotal lines)
        sum_others = sum(sorted_amts[:-1])
        
        # If the sum of all other numbers is close to the max number, it's structurally sound.
        # If it's wildly off, flag it as a logical math anomaly.
        if total_claimed > 0 and abs(total_claimed - sum_others) > (total_claimed * 0.2):
            rules_reasons.append(f"🧠 Logical Math Anomaly: The smaller amounts (sum={sum_others}) do not logically roll up into the claimed total ({total_claimed}). Did a human edit the total without recalculating taxes?")
            rules_score += 30
            
    return min(rules_score, 100), rules_reasons
