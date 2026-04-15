from scraper.client import UpworkClient
from scraper.config import HEADERS, COOKIES
from scraper.parser import parse_jobs
import json

payload = {
  "query": """
  query UserJobSearch($requestVariables: UserJobSearchV1Request!) {
    search {
      universalSearchNuxt {
        userJobSearchV1(request: $requestVariables) {
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
  
      
    paymentVerified: payment 
    {
      key
      value
    }
  
    proposals 
    {
      key
      value
    }
  
    previousClients 
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
            
    isSTSVectorSearchResult
    applied
    upworkHistoryData {
      client {
        paymentVerificationStatus
        country
        totalReviews
        totalFeedback
        hasFinancialPrivacy
        totalSpent {
          isoCurrencyCode
          amount
        }
      }
      freelancerClientRelation {
        lastContractRid
        companyName
        lastContractTitle
      }
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
                
    enterpriseJob
    personsToHire
    premium
    totalApplicants
  
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
      "sort": "relevance+desc",
      "highlight": True,
      "paging": {
        "offset": 10,
        "count": 10
      }
    }
  }
}

def main():
    client = UpworkClient(HEADERS, COOKIES)
    print("Fetching jobs from Upwork...")
    response = client.fetch_jobs(payload)
    
    print("Status Code:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        jobs = parse_jobs(data)
        
        print(f"\nFound {len(jobs)} jobs.\n")
        for idx, job in enumerate(jobs, 1):
            print(f"[{idx}] {job['title']}")
            print(f"    Budget: {job['budget']}")
            print(f"    Skills: {', '.join(job['skills'])[:100]}...")
            print("-" * 50)
    else:
        print("Error fetching jobs. Response text:")
        print(response.text)

if __name__ == "__main__":
    main()
