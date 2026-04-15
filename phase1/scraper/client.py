import requests

class UpworkClient:
    def __init__(self, headers, cookies):
        self.session = requests.Session()
        self.headers = headers
        self.cookies = cookies

    def fetch_jobs(self, payload):
        response = self.session.post(
            "https://www.upwork.com/api/graphql/v1?alias=userJobSearch",
            headers=self.headers,
            cookies=self.cookies,
            json=payload
        )
        return response
