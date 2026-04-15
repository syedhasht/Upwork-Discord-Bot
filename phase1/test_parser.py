import json
from scraper.parser import parse_jobs

try:
    with open("sample_response.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = parse_jobs(data)

    print(f"Successfully parsed {len(jobs)} jobs!\n")
    for idx, job in enumerate(jobs[:3], 1):
        print(f"[{idx}] Title:  {job['title']}")
        print(f"    Budget: {job['budget']}")
        print(f"    Skills: {', '.join(job['skills'])[:100]}")
        print("-" * 50)
except Exception as e:
    print("Error:", e)
