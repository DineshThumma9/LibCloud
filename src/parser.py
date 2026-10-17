import re
from collections import defaultdict
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from constants import (
    HOSTING_BLOCKLIST,
    NOISE,
    NORM,
    clean_pkg,
    pkg_to_lang,
)
from models import ProjectLinks, PKGInfo

can: set[str] = set()

FILE_REGEX = {
    "requirements.txt": [
        {   # skip comments (#) and pip options (-e, --index-url, etc.)
            "block": None,
            "name": re.compile(r'^(?!\s*#)(?!\s*-)\s*([A-Za-z][A-Za-z0-9._-]*)', re.MULTILINE),
        },
    ],
    "pyproject.toml": [
        {   # PEP 621: [project] dependencies = ["fastapi>=0.1", ...]
            "block": re.compile(r'^\s*dependencies\s*=\s*\[([^\]]*)\]', re.MULTILINE),
            "name": re.compile(r'"([A-Za-z][A-Za-z0-9._-]*)'),
        },
        {   # Poetry: [tool.poetry.dependencies] \n name = "^1.0"
            "block": re.compile(r'\[tool\.poetry\.dependencies\]([^\[]*)'),
            "name": re.compile(r'^([A-Za-z][A-Za-z0-9._-]*)\s*=', re.MULTILINE),
        },
    ],
    "pom.xml": [
        {   # captures (groupId, artifactId) pairs — joined below into
            # "groupId:artifactId" so it matches the GitHub API's own
            # Maven packageName format and reuses the same clean_pkg lambda
            "block": None,
            "name": re.compile(
                r'<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>',
                re.DOTALL,
            ),
        },
    ],
    "package.json": [
        {   # isolate the dependencies/devDependencies object first so
            # "name", "scripts", etc. elsewhere in the file can't match
            "block": re.compile(r'"(?:dependencies|devDependencies)"\s*:\s*\{([^}]*)\}'),
            "name": re.compile(r'"((?:@[\w.-]+/)?[\w.-]+)"\s*:\s*"'),
        },
    ],
}


def process(pkg_content: str, pkg_origin: str) -> defaultdict[str, PKGInfo]:
    pkg_dic = defaultdict(PKGInfo)
    for cfg in FILE_REGEX.get(pkg_origin, []):
        text = pkg_content
        if cfg["block"] is not None:
            text = "\n".join(cfg["block"].findall(pkg_content))
        for raw in cfg["name"].findall(text):
            if isinstance(raw, tuple):      # pom.xml's (groupId, artifactId)
                raw = ":".join(raw)
            norm, lang = normalize_pkg(raw, pkg_origin)
            if norm and lang:
                pkg = pkg_dic[norm]
                pkg.count += 1
                pkg.dep_origin = lang
                pkg.raw_names.add(raw)
    return pkg_dic


def normalize_pkg(dep_name: str, dep_origin: str) -> tuple[Optional[str], Optional[str]]:
    fname = Path(dep_origin).name
    lang = pkg_to_lang.get(fname)
    if not lang:
        return None, None
    func = clean_pkg.get(lang)
    cln_pkg = func(dep_name) if func else dep_name
    if cln_pkg in NOISE.get(lang, set()):
        can.add(cln_pkg)
        return None, None
    norm_name = NORM.get(lang, {}).get(cln_pkg, cln_pkg)
    return norm_name, lang


def parse_urls_to_links(urls: list[str]) -> ProjectLinks:
    custom_domain = None
    github_owner = None
    for url in urls:
        if not url or not isinstance(url, str):
            continue

        clean = re.sub(r"^git\+?", "", url).strip()
        if not clean:
            continue

        if not clean.startswith(("http://", "https://")):
            clean = f"https://{clean.lstrip('/')}"

        try:
            parsed = urlparse(clean)
            host = parsed.netloc.lower()
            if ":" in host:
                host = host.split(":")[0]
            if host.startswith("www."):
                host = host[4:]

            if "github.com" in host and not github_owner:
                path_parts = [p for p in parsed.path.strip("/").split("/") if p]
                if len(path_parts) >= 1:
                    github_owner = path_parts[0]
                continue

            if host and host not in HOSTING_BLOCKLIST:
                if custom_domain is None:
                    custom_domain = host
        except Exception:
            pass

    return ProjectLinks(custom_domain=custom_domain, github_owner=github_owner)
