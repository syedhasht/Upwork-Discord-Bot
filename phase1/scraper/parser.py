def _clean(text: str) -> str:
    """Strip Upwork's H^word^H search highlight markers."""
    if not text:
        return text or ""
    return text.replace("H^", "").replace("^H", "").strip()

def parse_jobs(response_json):
    jobs = []

    try:
        # Navigate through the visitorJobSearch response structure
        results = response_json.get("data", {}).get("search", {}).get("universalSearchNuxt", {}).get("visitorJobSearchV1", {}).get("results", [])

        for result in results:
            job_info = result.get("jobTile", {}).get("job", {})
            
            # Formulate the budget properly
            budget = "N/A"
            if job_info.get("jobType") == "FIXED":
                budget_amount = job_info.get("fixedPriceAmount", {}).get("amount", "N/A")
                currency = job_info.get("fixedPriceAmount", {}).get("isoCurrencyCode", "USD")
                budget = f"{budget_amount} {currency}"
            elif job_info.get("jobType") == "HOURLY":
                min_rate = job_info.get("hourlyBudgetMin")
                max_rate = job_info.get("hourlyBudgetMax")
                if min_rate is not None and max_rate is not None:
                    budget = f"${min_rate} - ${max_rate} / hr"
                elif min_rate is not None:
                    budget = f"From ${min_rate} / hr"
                elif max_rate is not None:
                    budget = f"Up to ${max_rate} / hr"

            skills = [skill.get("prefLabel") for skill in result.get("ontologySkills", [])]

            jobs.append({
                "id": result.get("id"),
                "title": _clean(result.get("title", "")),
                "description": _clean(result.get("description", "")),
                "job_type": job_info.get("jobType", "N/A"),
                "budget": budget,
                "skills": skills,
                "link": f"https://www.upwork.com/jobs/{job_info.get('ciphertext', '')}"
            })

    except Exception as e:
        print("Parsing error:", e)

    return jobs
