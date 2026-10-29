from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from app.constants import HOSTING_BLOCKLIST
import re 
from urllib.parse import urlparse



class ProjectLinks(BaseModel):
    custom_domain: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo:Optional[str] = None 




    @classmethod
    def parse_urls_to_links(cls, urls: list[str]) -> ProjectLinks:
        custom_domain = None
        github_owner = None
        github_repo = None 
        for url in urls:
            if not url or not isinstance(url, str):
                continue

            clean = url.strip()
            # Normalize SSH and git protocols: git@github.com:owner/repo.git or git+ssh://
            clean = re.sub(r"^(?:git\+)?(?:ssh|https?)://git@", "https://", clean)
            clean = re.sub(r"^git@([^:/]+):", r"https://\1/", clean)
            clean = re.sub(r"^git\+?", "", clean).strip()
            if not clean:
                continue

            if not clean.startswith(("http://", "https://")):
                clean = f"https://{clean.lstrip('/')}"

            try:
                parsed = urlparse(clean)
                host = parsed.netloc.lower()
                if ":" in host:
                    host = host.split(":")[0]

                # Check for github repository
                if (host == "github.com" or host.endswith(".github.com")) and not github_owner:
                    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
                    non_repo_routes = {
                        "sponsors", "orgs", "users", "search", "features", "pricing",
                        "marketplace", "about", "topics", "pulls", "issues", "settings"
                    }
                    if path_parts:
                        first = path_parts[0].lower()
                        if first in ("orgs", "users", "sponsors") and len(path_parts) >= 2:
                            github_owner = path_parts[1].replace(".git", "")
                        elif first not in non_repo_routes:
                            github_owner = path_parts[0].replace(".git", "")
                            if len(path_parts) >= 2:
                                github_repo = path_parts[1].replace(".git", "")
                    continue

                clean_host = host[4:] if host.startswith("www.") else host
                is_blocked_host = any(clean_host == b or clean_host.endswith("." + b) for b in HOSTING_BLOCKLIST)
                if clean_host and not is_blocked_host:
                    if custom_domain is None:
                        # Prefer original host (e.g. www.python-httpx.org) for accurate favicon matching
                        custom_domain = host if host else clean_host
            except Exception:
                pass

        return ProjectLinks(custom_domain=custom_domain, github_owner=github_owner,github_repo=github_repo)




class PyPIResponse(BaseModel):
    info: dict = Field(default_factory=dict)

    def extract_links(self) -> ProjectLinks:
        urls: list[str] = []
        if isinstance(self.info, dict):
            if self.info.get("home_page"):
                urls.append(str(self.info["home_page"]))
            if self.info.get("project_url"):
                urls.append(str(self.info["project_url"]))
            project_urls = self.info.get("project_urls")
            if isinstance(project_urls, dict):
                urls.extend(str(v) for v in project_urls.values() if v)
        return ProjectLinks.parse_urls_to_links(urls)


class NPMResponse(BaseModel):
    homepage: Optional[str] = None
    repository: Optional[dict | str] = None

    def extract_links(self) -> ProjectLinks:
        urls: list[str] = []
        if self.homepage:
            urls.append(self.homepage)
        if isinstance(self.repository, dict):
            repo_url = self.repository.get("url")
            if repo_url and isinstance(repo_url, str):
                urls.append(repo_url)
        elif isinstance(self.repository, str):
            urls.append(self.repository)
        return ProjectLinks.parse_urls_to_links(urls)


class MavenResponse(BaseModel):
    response: dict = Field(default_factory=dict)

    def extract_links(self) -> ProjectLinks:
        urls: list[str] = []
        docs = self.response.get("docs", [])
        if isinstance(docs, list) and docs:
            first = docs[0]
            g = first.get("g", "")
            if g.startswith("com.github."):
                parts = g.split(".")
                if len(parts) >= 3:
                    urls.append(f"https://github.com/{parts[2]}")
        return ProjectLinks.parse_urls_to_links(urls)


class CratesIOResponse(BaseModel):
    crate: dict = Field(default_factory=dict)

    def extract_links(self) -> ProjectLinks:
        urls: list[str] = []
        if isinstance(self.crate, dict):
            for k in ("repository", "homepage", "documentation"):
                val = self.crate.get(k)
                if val and isinstance(val, str):
                    urls.append(val)
        return ProjectLinks.parse_urls_to_links(urls)


class RubyGemsResponse(BaseModel):
    source_code_uri: Optional[str] = None
    homepage_uri: Optional[str] = None
    project_uri: Optional[str] = None
    bug_tracker_uri: Optional[str] = None

    def extract_links(self) -> ProjectLinks:
        urls: list[str] = []
        for u in (self.source_code_uri, self.homepage_uri, self.project_uri, self.bug_tracker_uri):
            if u and isinstance(u, str):
                urls.append(u)
        return ProjectLinks.parse_urls_to_links(urls)


PKG_MODELS = {
    "ts": NPMResponse,
    "py": PyPIResponse,
    "java": MavenResponse,
    "kotlin": MavenResponse,
    "rust": CratesIOResponse,
    "ruby": RubyGemsResponse,
}


from typing import Any 


class PKGInfo(BaseModel):
    dep_origin: str = ""
    count: int = 0
    raw_names: set[str] = Field(default_factory=set)
    icon: Optional[str] = None

    def merge(self, other: PKGInfo) -> PKGInfo:
        if not isinstance(other, PKGInfo):
            raise TypeError(f"Expected PKGInfo, got {type(other).__name__}")
        self.count += other.count
        if not self.dep_origin and other.dep_origin:
            self.dep_origin = other.dep_origin
        self.raw_names |= other.raw_names
        return self


def merge_pkg_dicts(target: dict[str, PKGInfo], source: dict[str, PKGInfo]) -> dict[str, PKGInfo]:
    for norm, info in source.items():
        if norm in target:
            target[norm].merge(info)
        else:
            target[norm] = PKGInfo(
                count=info.count,
                dep_origin=info.dep_origin,
                raw_names=set(info.raw_names)
            )
    return target



class Error(BaseModel):
    phase: str
    message: str
    retryable: str
    run_id: str = ""


class Event(BaseModel):
    job_id: str
    type: str
    ts: float
    seq: int
    data: Any
