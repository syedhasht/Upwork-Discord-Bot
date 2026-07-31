import re

def filter_jobs(jobs: list, min_budget: float = 0.0, keyword: str = "python") -> list:
    """
    Filters out jobs that:
    1. Do not match the target keyword (using flexible matching) in title/description/skills.
    2. Fall strictly below the target minimum budget (when a parseable budget is found).
    """
    filtered = []
    kw_clean = keyword.lower().strip()
    
    for job in jobs:
        # Strip Upwork's H^word^H highlight markers before matching
        skills_list = job.get('skills') or []
        skills_str = " ".join(skills_list)
        raw_text = f"{job['title']} {job['description']} {skills_str}"
        clean_text = raw_text.replace("H^", "").replace("^H", "").lower()
        
        # Smart, relaxed keyword checking
        match_found = False
        
        if kw_clean == "ai voice agent":
            # For AI voice agent, match if it contains "ai voice agent" literally,
            # or if it has voice-related terms AND AI-related terms
            has_voice = any(w in clean_text for w in ["voice", "audio", "calling", "receptionist", "caller", "telephony", "vapi", "retell", "bland", "elevenlabs", "speech", "tts", "stt"])
            has_ai = any(w in clean_text for w in ["ai", "artificial intelligence", "agent", "bot", "assistant", "llm", "openai", "claude"])
            if ("ai voice agent" in clean_text) or (has_voice and has_ai):
                match_found = True
        elif kw_clean == "machine learning":
            # For machine learning, match if "machine learning" is present,
            # or if "ml" is present as a distinct word
            has_ml = re.search(r'\bml\b', clean_text) is not None
            if ("machine learning" in clean_text) or has_ml:
                match_found = True
        else:
            # For multi-word keywords, check if all words are present in any order
            # (e.g. "fastapi developer" matches a text containing both "fastapi" and "developer")
            tokens = kw_clean.split()
            if tokens:
                if all(t in clean_text for t in tokens):
                    match_found = True
            else:
                if kw_clean in clean_text:
                    match_found = True
                    
        if not match_found:
            continue
            
        # Optional Budget Filter (simplified float parse for mock)
        if min_budget > 0:
            budget_str = str(job.get('budget', '')).replace('$', '').replace(',', '')
            # Very aggressive parsing attempt to grab the first numerical block
            parsed_val = 0.0
            try:
                words = budget_str.split()
                if words:
                    parsed_val = float(words[0])
            except ValueError:
                pass
                
            if parsed_val > 0 and parsed_val < min_budget:
                continue
                
        filtered.append(job)
        
    return filtered

