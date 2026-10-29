import json
import logging
import re
import tomllib
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Optional, Union

from app.constants import (
    NOISE,
    NORM,
    NORM_PATTERNS,
    clean_pkg,
    pkg_to_lang,
)
from app.models import PKGInfo
from app.reporting.csv import write_csv_rows

log = logging.getLogger(__name__)


def _extract_pep508_names(deps: list) -> list[str]:
    raws = []
    for dep in deps:
        if isinstance(dep, str):
            m = re.match(r"^([A-Za-z0-9_.-]+)", dep.strip())
            if m:
                raws.append(m.group(1))
    return raws


def parse_pyproject(content: str) -> list[str]:
    raws: list[str] = []
    try:
        data = tomllib.loads(content)
        # PEP 621 dependencies
        raws.extend(_extract_pep508_names(data.get("project", {}).get("dependencies", [])))

        # PEP 621 optional-dependencies
        for opt_list in data.get("project", {}).get("optional-dependencies", {}).values():
            if isinstance(opt_list, list):
                raws.extend(_extract_pep508_names(opt_list))

        # PEP 735 dependency-groups (uv, flit)
        for grp in data.get("dependency-groups", {}).values():
            if isinstance(grp, list):
                raws.extend(_extract_pep508_names(grp))

        # Poetry tool section
        poetry = data.get("tool", {}).get("poetry", {})
        if isinstance(poetry, dict):
            for sec_name in ("dependencies", "dev-dependencies"):
                for k in poetry.get(sec_name, {}).keys():
                    if k.lower() != "python":
                        raws.append(k)
            for grp in poetry.get("group", {}).values():
                if isinstance(grp, dict):
                    for k in grp.get("dependencies", {}).keys():
                        if k.lower() != "python":
                            raws.append(k)
    except Exception as e:
        log.debug("Falling back to regex for toml: %s", e)
        for m in re.finditer(r'["\']([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?(?:\s*[><=~^!].*?)?["\']', content):
            raws.append(m.group(1))
    return raws


def parse_package_json(content: str) -> list[str]:
    raws: list[str] = []
    # If there is preamble before the main JSON object (e.g. accidental CLI output), slice from first {
    start = content.find("{")
    clean_content = content[start:] if start != -1 else content
    try:
        data = json.loads(clean_content)
        if isinstance(data, dict):
            for sec in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                d = data.get(sec, {})
                if isinstance(d, dict):
                    raws.extend(d.keys())
    except Exception as e:
        log.debug("Falling back to regex for json: %s", e)
        # Search specifically inside dependency blocks, avoiding top-level keys and scripts
        dep_blocks = re.findall(r'"(?:dev|peer|optional)?[Dd]ependencies"\s*:\s*\{([^}]+)\}', content)
        target_text = "\n".join(dep_blocks) if dep_blocks else content
        for m in re.finditer(r'"((?:@[\w.-]+/)?[\w.-]+)"\s*:\s*"', target_text):
            raws.append(m.group(1))
    return raws


def parse_requirements(content: str) -> list[str]:
    raws: list[str] = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "--", "-r", "-f", "-i")):
            continue
        if "#egg=" in line:
            raws.append(line.split("#egg=", 1)[1].strip())
            continue
        if line.startswith("-e "):
            line = line[3:].strip()
        line = line.split(" #", 1)[0].split(";", 1)[0].strip()
        m = re.match(r"^([A-Za-z0-9_.-]+)", line)
        if m:
            raws.append(m.group(1))
    return raws


def parse_pipfile(content: str) -> list[str]:
    raws: list[str] = []
    try:
        data = tomllib.loads(content)
        for section in ("packages", "dev-packages"):
            sec = data.get(section, {})
            if isinstance(sec, dict):
                for pkg in sec.keys():
                    if isinstance(pkg, str) and pkg.strip():
                        raws.append(pkg.strip())
    except Exception as e:
        log.warning("Failed parsing Pipfile: %s", e)
    return raws


def parse_pom_xml(content: str) -> list[str]:
    raws: list[str] = []
    try:
        root = ET.fromstring(content)
        for dep in root.iter():
            if dep.tag.endswith("dependency"):
                gid, aid = None, None
                for child in dep:
                    if child.tag.endswith("groupId") and child.text:
                        gid = child.text.strip()
                    elif child.tag.endswith("artifactId") and child.text:
                        aid = child.text.strip()
                if gid and aid:
                    raws.append(f"{gid}:{aid}")
    except Exception as e:
        log.debug("Falling back to regex for pom: %s", e)
        for m in re.finditer(r'<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>', content, re.DOTALL):
            raws.append(f"{m.group(1).strip()}:{m.group(2).strip()}")
    return raws


def parse_workflow(content: str) -> list[str]:
    return [
        m.group(1)
        for m in re.finditer(r'uses:\s*["\']?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:@[^\s"\']+)?)', content)
    ]


def parse_cargo_toml(content: str) -> list[str]:
    raws: list[str] = []
    try:
        data = tomllib.loads(content)
        sections = ("dependencies", "dev-dependencies", "build-dependencies")
        for sec in sections:
            d = data.get(sec, {})
            if isinstance(d, dict):
                raws.extend(d.keys())
        ws_deps = data.get("workspace", {}).get("dependencies", {})
        if isinstance(ws_deps, dict):
            raws.extend(ws_deps.keys())
        for target_cfg in data.get("target", {}).values():
            if isinstance(target_cfg, dict):
                for sec in sections:
                    d = target_cfg.get(sec, {})
                    if isinstance(d, dict):
                        raws.extend(d.keys())
    except Exception as e:
        log.debug("Falling back to regex for Cargo.toml: %s", e)
        for m in re.finditer(r'^\s*([A-Za-z0-9_-]+)\s*=', content, re.MULTILINE):
            raws.append(m.group(1))
    return raws


def parse_go_mod(content: str) -> list[str]:
    raws: list[str] = []
    in_block = False
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("require ("):
            in_block = True
            continue
        if in_block:
            if line.startswith(")"):
                in_block = False
                continue
            parts = line.split()
            if parts:
                raws.append(parts[0])
        elif line.startswith("require "):
            parts = line[len("require "):].strip().split()
            if parts:
                raws.append(parts[0])
    return raws


def parse_gemfile(content: str) -> list[str]:
    return [
        m.group(1)
        for m in re.finditer(r'^\s*gem\s+["\']([A-Za-z0-9_-]+)["\']', content, re.MULTILINE)
    ]


def parse_gradle(content: str) -> list[str]:
    raws: list[str] = []
    for m in re.finditer(r'(?:implementation|api|testImplementation|compileOnly|runtimeOnly|annotationProcessor)\s*\(?["\']([^:"\'\s]+):([^:"\'\s]+)(?::[^"\']*)?["\']\)?', content):
        raws.append(f"{m.group(1)}:{m.group(2)}")
    for m in re.finditer(r'group:\s*["\']([^"\']+)["\'],\s*name:\s*["\']([^"\']+)["\']', content):
        raws.append(f"{m.group(1)}:{m.group(2)}")
    return raws


FILE_PARSERS: dict[str, Callable[[str], list[str]]] = {
    "pyproject.toml": parse_pyproject,
    "package.json": parse_package_json,
    "requirements.txt": parse_requirements,
    "Pipfile": parse_pipfile,
    "pom.xml": parse_pom_xml,
    "build.gradle": parse_gradle,
    "build.gradle.kts": parse_gradle,
    "go.mod": parse_go_mod,
    "Cargo.toml": parse_cargo_toml,
    "Gemfile": parse_gemfile,
    "workflow": parse_workflow,
}

ACTION_PREFIX_NORM: dict[str, str] = {
    "actions/": "GitHub Actions",
    "docker/": "Docker",
    "azure/": "Azure",
    "aws-actions/": "AWS SDK",
    "google-github-actions/": "Google Cloud",
}


class DependencyParser:

    def __init__(self):
        self.can_records: list[dict] = []
        self._seen_filtered: set[tuple[str, str, str]] = set()
        self.unnormalized_records: list[dict] = []
        self._seen_unnormalized: set[tuple[str, str, str]] = set()
        self._unnorm_counts: Counter = Counter()

    def parser(self, pkg_content: str, pkg_origin: str) -> defaultdict[str, PKGInfo]:
        pkg_dic = defaultdict(PKGInfo)
        fname = Path(pkg_origin).name

        parse_fn = FILE_PARSERS.get(fname)
        if not parse_fn and ("workflow" in fname.lower() or fname.endswith((".yml", ".yaml"))):
            parse_fn = FILE_PARSERS.get("workflow")

        if not parse_fn:
            return pkg_dic

        for raw in parse_fn(pkg_content):
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
        if not lang and ("workflow" in str(dep_origin).lower() or fname.endswith((".yml", ".yaml"))):
            lang = "actions"

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

        clean_fn = clean_pkg.get(lang)
        cln_pkg = clean_fn(dep_name) if clean_fn else dep_name

        if cln_pkg in NOISE.get(lang, set()):
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

        if lang == "actions":
            for prefix, canonical in ACTION_PREFIX_NORM.items():
                if cln_pkg.startswith(prefix):
                    return canonical, lang

        norm_name = NORM.get(lang, {}).get(cln_pkg, None)
        if not norm_name:
            for pattern, canonical in NORM_PATTERNS.get(lang, ()):
                if pattern.match(cln_pkg):
                    norm_name = canonical
                    break
        if not norm_name:
            record_key = (dep_name, cln_pkg, dep_origin)
            self._unnorm_counts[(dep_name, cln_pkg, lang, fname, dep_origin)] += 1
            if record_key not in self._seen_unnormalized:
                self._seen_unnormalized.add(record_key)
                self.unnormalized_records.append({
                    "raw_name": dep_name,
                    "cleaned_name": cln_pkg,
                    "dep_origin": fname,
                    "origin_path": dep_origin,
                    "language": lang,
                    "reason": "missing_normalization",
                })
            return cln_pkg, lang

        return norm_name, lang

    def export_filtered_csv(self, filepath: Union[str, Path] = "filtered_packages.csv") -> Path:
        out_path = write_csv_rows(
            filepath,
            ["raw_name", "cleaned_name", "norm_name", "dep_origin", "language", "reason", "origin_path"],
            self.can_records,
        )
        log.info("✓ Exported %d filtered/noise package records to %s", len(self.can_records), out_path)
        return out_path

    def unnormalized_rows(self) -> list[dict]:
        return [
            {
                "cleaned_name": cln_pkg,
                "raw_name": raw_name,
                "count": count,
                "language": lang,
                "dep_origin": fname,
                "origin_path": dep_origin,
            }
            for (raw_name, cln_pkg, lang, fname, dep_origin), count in self._unnorm_counts.most_common()
        ]

    def export_unnormalized_csv(self, filepath: Union[str, Path] = "unnormalized_packages.csv") -> Path:
        rows = self.unnormalized_rows()
        out_path = write_csv_rows(
            filepath,
            ["cleaned_name", "raw_name", "count", "language", "dep_origin", "origin_path"],
            rows,
        )
        log.info("✓ Exported %d unnormalized package records to %s", len(rows), out_path)
        return out_path
