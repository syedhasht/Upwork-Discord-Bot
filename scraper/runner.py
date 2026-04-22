from core.client import UpworkClient
from core.config import HEADERS, COOKIES
from core.parser import parse_jobs

payload = {
    "query": """
  query VisitorJobSearch($requestVariables: VisitorJobSearchV1Request!) {
    search {
      universalSearchNuxt {
        visitorJobSearchV1(request: $requestVariables) {
          paging {
            total
            offset
            count
          }
          
    facets {
      jobType 
    {
      key
      value
    }
  
      workload 
    {
      key
      value
    }
  
      clientHires 
    {
      key
      value
    }
  
      durationV3 
    {
      key
      value
    }
  
      amount 
    {
      key
      value
    }
  
      contractorTier 
    {
      key
      value
    }
  
      contractToHire 
    {
      key
      value
    }
  
      
    }
  
          results {
            id
            title
            description
            relevanceEncoded
            ontologySkills {
              uid
              parentSkillUid
              prefLabel
              prettyName: prefLabel
              freeText
              highlighted
            }
            
            jobTile {
              job {
                id
                ciphertext: cipherText
                jobType
                weeklyRetainerBudget
                hourlyBudgetMax
                hourlyBudgetMin
                hourlyEngagementType
                contractorTier
                sourcingTimestamp
                createTime
                publishTime
                
                hourlyEngagementDuration {
                  rid
                  label
                  weeks
                  mtime
                  ctime
                }
                fixedPriceAmount {
                  isoCurrencyCode
                  amount
                }
                fixedPriceEngagementDuration {
                  id
                  rid
                  label
                  weeks
                  ctime
                  mtime
                }
              }
            }
          }
        }
      }
    }
  }
  """,
    "variables": {
        "requestVariables": {
            "userQuery": "python",
            "sort": "recency",
            "highlight": True,
            "paging": {
                "offset": 0,
                "count": 20
            }
        }
    }
}

def run_scraper(keyword="python", count=10):
    # Always reload config from disk to pick up the latest tokens
    # written by the Cloudflare solver on any previous keyword's refresh
    import importlib
    import core.config as _cfg
    importlib.reload(_cfg)
    headers = _cfg.HEADERS
    cookies = _cfg.COOKIES

    # Dynamically update the payload
    payload["variables"]["requestVariables"]["userQuery"] = keyword
    payload["variables"]["requestVariables"]["paging"]["count"] = count

    client = UpworkClient(headers, cookies)
    print(f"Fetching {count} jobs from Upwork for keyword: {keyword}...")
    response = client.fetch_jobs(payload)

    print("Status Code:", response.status_code)

    if response.status_code == 200:
        data = response.json()
        jobs = parse_jobs(data)
        print(f"\nFound {len(jobs)} jobs.\n")
        return jobs
    else:
        print("Error fetching jobs. Response text:")
        print(response.text)
        return []

if __name__ == "__main__":
    jobs = run_scraper()
    for idx, job in enumerate(jobs, 1):
        print(f"[{idx}] {job['title']}")
        print(f"    Budget: {job['budget']}")
        print(f"    Posted: {job.get('posted_on', 'N/A')}")
        print(f"    Skills: {', '.join(job['skills'])[:100]}...")
        print("-" * 50)
