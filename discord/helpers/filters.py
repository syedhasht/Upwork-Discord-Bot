import re
import datetime

def filter_jobs(jobs: list, min_budget: float = 0.0, keyword: str = "python", max_age_hours: float = 1.0) -> list:
    """
    Filters out jobs that:
    1. Are hourly jobs (only fixed-price jobs allowed).
    2. Are older than max_age_hours (default: max 1 hour old).
    3. Do not match the target keyword (using flexible matching) in title/description/skills.
    4. Fall strictly below the target minimum budget (when a parseable budget is found).
    """
    filtered = []
    kw_clean = keyword.lower().strip()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    for job in jobs:
        # Exclude hourly jobs
        job_type = str(job.get("job_type", "")).upper()
        if job_type == "HOURLY" or "/ hr" in str(job.get("budget", "")).lower():
            continue

        # Exclude jobs older than max_age_hours (default: max 1 hour old)
        if max_age_hours is not None and max_age_hours > 0:
            raw_time = job.get("created_at_raw")
            if not raw_time:
                continue
            try:
                if isinstance(raw_time, str):
                    dt = datetime.datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                else:
                    dt = datetime.datetime.fromtimestamp(int(raw_time) / 1000, tz=datetime.timezone.utc)
                age_seconds = (now_utc - dt).total_seconds()
                # Allow a small 5-minute clock drift into the future (-300s), but reject if older than cutoff
                if age_seconds > (max_age_hours * 3600) or age_seconds < -300:
                    continue
            except Exception:
                continue
        # Strip Upwork's H^word^H highlight markers before matching
        skills_list = job.get('skills') or []
        skills_str = " ".join(skills_list)
        raw_text = f"{job['title']} {job['description']} {skills_str}"
        clean_text = raw_text.replace("H^", "").replace("^H", "").lower()
        
        # Exclude jobs referencing India or Pakistan
        country_blacklist = [r'\bpakistan\b', r'\bpakistani\b', r'\bindia\b', r'\bindian\b', r'\bpkr\b', r'\binr\b']
        if any(re.search(pat, clean_text) for pat in country_blacklist):
            continue
        
        # Smart, relaxed keyword checking
        match_found = False
        
        if kw_clean == "ai voice agent":
            # For AI voice agent, match if it contains "ai voice agent" literally,
            # or if it has voice-related terms AND AI-related terms
            has_voice = any(w in clean_text for w in ["voice", "audio", "calling", "receptionist", "caller", "telephony", "vapi", "retell", "bland", "elevenlabs", "speech", "tts", "stt"])
            has_ai = any(w in clean_text for w in ["ai", "artificial intelligence", "agent", "bot", "assistant", "llm", "openai", "claude"])
            if ("ai voice agent" in clean_text) or (has_voice and has_ai):
                match_found = True
        elif kw_clean in ["chatbot", "chat bot"]:
            # For chatbot, match "chatbot", "chat bot", or conversational + bot/agent
            has_bot = "bot" in clean_text or "agent" in clean_text
            has_chat = "chat" in clean_text or "conversational" in clean_text
            if ("chatbot" in clean_text) or ("chat bot" in clean_text) or (has_chat and has_bot):
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

