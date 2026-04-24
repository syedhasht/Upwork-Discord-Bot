from core.client import UpworkClient
try:
    from core.config import HEADERS, COOKIES
except ImportError:
    HEADERS = {}
    COOKIES = {}
from core.parser import parse_jobs
import logging

logger = logging.getLogger("jobhunt")

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

def run_scraper(keyword="python", count=10, force_refresh=False):
    # Dynamically update the payload
    payload["variables"]["requestVariables"]["userQuery"] = keyword
    payload["variables"]["requestVariables"]["paging"]["count"] = count

    # UpworkClient now handles loading from session.json automatically
    client = UpworkClient()
    logger.debug(f"Fetching {count} jobs for keyword: '{keyword}'")
    response = client.fetch_jobs(payload, force_refresh=force_refresh)

    if response is None:
        logger.error(f"Failed to fetch jobs for '{keyword}'. Network error or timeout.")
        return []

    logger.debug(f"Upwork response status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        jobs = parse_jobs(data)
        logger.debug(f"Received {len(jobs)} jobs for '{keyword}'")
        return jobs
    else:
        logger.error(f"Failed to fetch jobs for '{keyword}'. Status: {response.status_code}")
        return []

if __name__ == "__main__":
    jobs = run_scraper()
    for idx, job in enumerate(jobs, 1):
        print(f"[{idx}] {job['title']}")
        print(f"    Budget: {job['budget']}")
        print(f"    Posted: {job.get('posted_on', 'N/A')}")
        print(f"    Skills: {', '.join(job['skills'])[:100]}...")
        print("-" * 50)
