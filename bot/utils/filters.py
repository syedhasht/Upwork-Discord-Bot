def filter_jobs(jobs: list, min_budget: float = 0.0, keyword: str = "python") -> list:
    """
    Filters out jobs that:
    1. Do not contain the target keyword (case insensitive) in title/description/skills.
    2. Fall strictly below the target minimum budget (when a parseable budget is found).
    """
    filtered = []
    
    for job in jobs:
        # Strip Upwork's H^word^H highlight markers before matching
        raw_text = f"{job['title']} {job['description']} {job.get('skills', '')}"
        clean_text = raw_text.replace("H^", "").replace("^H", "").lower()
        
        if keyword.lower() not in clean_text:
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
