import httpx 

class GraphGithubClient:
    def __init__(self,token,url:str="https://api.github.com/graphql",timeout:int=30,headers:dict={}):
        self.token = token
        self.url = url
        headers = {
            "Content-Type":"application/json",
            "Accept":"application/json",
            "User-Agent":"GithubAnalysis"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.client = httpx.AsyncClient(timeout=timeout,headers=headers)

    async def __aenter__(self):
        return self

    async def __aexit__(self,*args):
        await self.close()

    async def execute(self,variables,headers:dict | None = None):
        try:
            response = await self.client.post(self.url,json=variables or {},headers=headers)
            if response.status_code == 200:
                data = response.json().get("data",{})
                if "errors" in data:
                    print(f"GraphQL errors : {data['errors']}")

                return data
            print(f"HTTP error :{response.status_code}")
            return None 
            
        except Exception as e:
            print(f"Error has occured with coden Error:{str(e)}")
            return None 
    async def close(self):
        await self.client.aclose()
