import csv
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

from constants import (
    HOSTING_BLOCKLIST,
    NOISE,
    NORM,
    clean_pkg,
    pkg_to_lang,
)
from models import ProjectLinks, PKGInfo

log = logging.getLogger(__name__)

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




class DependencyParser:

    def __init__(self):
        self.can: set[str] = set()
        self.can_records: list[dict] = []
        self._seen_filtered: set[tuple[str, str, str]] = set()

    def parser(self, pkg_content: str, pkg_origin: str) -> defaultdict[str, PKGInfo]:
        pkg_dic = defaultdict(PKGInfo)
        for cfg in FILE_REGEX.get(pkg_origin, []):
            text = pkg_content
            if cfg["block"] is not None:
                text = "\n".join(cfg["block"].findall(pkg_content))
            for raw in cfg["name"].findall(text):
                if isinstance(raw, tuple):      # pom.xml's (groupId, artifactId)
                    raw = ":".join(raw)
                norm, lang = self.normalize_pkg(raw, pkg_origin)
                if norm and lang:
                    pkg = pkg_dic[norm]
                    pkg.count += 1
                    pkg.dep_origin = lang
                    pkg.raw_names.add(raw)
        return pkg_dic

    parse = parser
    process = parser

    def normalize_pkg(self, dep_name: str, dep_origin: str) -> tuple[Optional[str], Optional[str]]:
        fname = Path(dep_origin).name
        lang = pkg_to_lang.get(fname)
        if not lang:
            record_key = (dep_name, dep_name, dep_origin)
            if record_key not in self._seen_filtered:
                self._seen_filtered.add(record_key)
                self.can_records.append({
                    "raw_name": dep_name,
                    "cleaned_name": dep_name,
                    "norm_name": "",
                    "dep_origin": fname,
                    "origin_path": dep_origin,
                    "language": "unknown",
                    "reason": "unsupported_manifest",
                })
            return None, None

        func = clean_pkg.get(lang)
        cln_pkg = func(dep_name) if func else dep_name
        if cln_pkg in NOISE.get(lang, set()):
            self.can.add(cln_pkg)
            record_key = (dep_name, cln_pkg, dep_origin)
            if record_key not in self._seen_filtered:
                self._seen_filtered.add(record_key)
                self.can_records.append({
                    "raw_name": dep_name,
                    "cleaned_name": cln_pkg,
                    "norm_name": "",
                    "dep_origin": fname,
                    "origin_path": dep_origin,
                    "language": lang,
                    "reason": "noise_blocklist",
                })
            return None, None
        norm_name = NORM.get(lang, {}).get(cln_pkg, cln_pkg)
        return norm_name, lang

    def export_filtered_csv(self, filepath: Union[str, Path] = "filtered_packages.csv") -> Path:
        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["raw_name", "cleaned_name", "norm_name", "dep_origin", "language", "reason", "origin_path"]
            )
            writer.writeheader()
            writer.writerows(self.can_records)
        log.info("✓ Exported %d filtered/noise package records to %s", len(self.can_records), out_path)
        return out_path

