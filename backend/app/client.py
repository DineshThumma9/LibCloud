import logging

import httpx

log = logging.getLogger(__name__)


class GraphGithubClient:
    def __init__(self, token, url: str = "https://api.github.com/graphql", timeout: int = 30, headers: dict | None = None):
        self.token = token
        self.url = url
        req_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "GithubAnalysis"
        }
        if headers:
            req_headers.update(headers)
        if self.token:
            req_headers["Authorization"] = f"Bearer {self.token}"
        self.client = httpx.AsyncClient(timeout=timeout, headers=req_headers)

    async def __aenter__(self):
        return self

    async def __aexit__(self,*args):
        await self.close()

    async def execute(self, variables, headers: dict | None = None):
        try:
            response = await self.client.post(self.url, json=variables or {}, headers=headers)
            if response.status_code == 200:
                body = response.json() or {}
                if "errors" in body and body["errors"]:
                    log.warning("GraphQL errors: %s", body["errors"])
                return body.get("data")
            log.error("HTTP error: %s", response.status_code)
            return None 
            
        except Exception as e:
            log.error("Error has occurred with code Error: %s", str(e))
            return None 
    async def close(self):
        await self.client.aclose()
