from typing import Optional
from pydantic import BaseModel, Field


class ProjectLinks(BaseModel):
    custom_domain: Optional[str] = None
    github_owner: Optional[str] = None


class PyPIResponse(BaseModel):
    info: dict = Field(default_factory=dict)

    def extract_links(self) -> ProjectLinks:
        from parser import parse_urls_to_links
        urls: list[str] = []
        if isinstance(self.info, dict):
            if self.info.get("home_page"):
                urls.append(str(self.info["home_page"]))
            if self.info.get("project_url"):
                urls.append(str(self.info["project_url"]))
            project_urls = self.info.get("project_urls")
            if isinstance(project_urls, dict):
                urls.extend(str(v) for v in project_urls.values() if v)
        return parse_urls_to_links(urls)


class NPMResponse(BaseModel):
    homepage: Optional[str] = None
    repository: Optional[dict | str] = None

    def extract_links(self) -> ProjectLinks:
        from parser import parse_urls_to_links
        urls: list[str] = []
        if self.homepage:
            urls.append(self.homepage)
        if isinstance(self.repository, dict):
            repo_url = self.repository.get("url")
            if repo_url and isinstance(repo_url, str):
                urls.append(repo_url)
        elif isinstance(self.repository, str):
            urls.append(self.repository)
        return parse_urls_to_links(urls)


class MavenResponse(BaseModel):
    response: dict = Field(default_factory=dict)

    def extract_links(self) -> ProjectLinks:
        from parser import parse_urls_to_links
        urls: list[str] = []
        docs = self.response.get("docs", [])
        if isinstance(docs, list) and docs:
            first = docs[0]
            g = first.get("g", "")
            if g.startswith("com.github."):
                parts = g.split(".")
                if len(parts) >= 3:
                    urls.append(f"https://github.com/{parts[2]}")
        return parse_urls_to_links(urls)


PKG_MODELS = {
    "ts": NPMResponse,
    "py": PyPIResponse,
    "java": MavenResponse,
}



class PKGInfo(BaseModel):
    dep_origin: str = ""
    count: int = 0
    raw_names: set[str] = Field(default_factory=set)
    icon: Optional[str] = None
    sha: Optional[str] = None

