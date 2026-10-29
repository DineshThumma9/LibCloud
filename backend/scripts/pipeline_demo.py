"""
End-to-end test for the full pipeline:
  fetch_all_repos_deps → ImageResolver.resolve → transform_wordcloud

Reads GITHUB_TOKEN and GITHUB_USERNAME from ../.env
Writes the resulting SVG to output.svg so you can open it in a browser.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# ── load .env ──────────────────────────────────────────────────────────────
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

TOKEN    = os.environ.get("GITHUB_TOKEN", "")
USERNAME = os.environ.get("GITHUB_USERNAME", "")

if not USERNAME:
    print("ERROR: GITHUB_USERNAME not set in .env")
    sys.exit(1)

# ── logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("run.log", mode="w", encoding="utf-8"),
    ],
)

# ── pipeline ───────────────────────────────────────────────────────────────
from app.config import settings
from app.reporting.ops import DepOpsLogger
from app.reporting.runs import RunContext
from app.services.scanning import GraphGithubAPI
from app.services.icons import ImageResolver
from app.services.render import transform_wordcloud


async def run():
    run_ctx = RunContext.create(USERNAME)
    report_dir = Path(settings.runs_dir) / run_ctx.username / run_ctx.run_id
    report_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Testing pipeline for: {USERNAME}")
    print(f"  Run:    {run_ctx.run_id}")
    print(f"  Token:  {'set ✓' if TOKEN else 'NOT SET (public repos only)'}")
    print(f"{'='*60}\n")

    # Step 1 — fetch all deps
    async with GraphGithubAPI(USERNAME, token=TOKEN or None, report_dir=report_dir) as api:
        pkg_dic = await api.fetch_all_repos_deps()
    top_10 = sorted(pkg_dic.items(), key=lambda x: x[1].count, reverse=True)
    print(f"\n✓ Step 1 done — {len(pkg_dic)} unique packages")
    print(f"  Top 10: {[(k, v.count) for k, v in top_10]}\n")

    if not pkg_dic:
        print("⚠ No packages found — check token / username")
        return

    # Step 2 — resolve packages to icons (CDNs + Registry fallback)
    all_packages = sorted(pkg_dic.items(), key=lambda x: x[1].count, reverse=True)
    async with ImageResolver(github_token=TOKEN, exporter=DepOpsLogger(report_dir)) as resolver:
        badge_dic = await resolver.resolve(all_packages)
    print(f"✓ Step 2 done — {len(badge_dic)} badge icons resolved\n")

    failed_count = len(resolver.failed_icons)
    if failed_count:
        print(f"  ⚠ {failed_count} packages had no icon found across all sources (see failed_icons.csv)\n")

    # Step 3 — render wordcloud SVGs (web: max space full view, readme: standard GitHub card)
    svg_web = transform_wordcloud(badge_dic, preset="web")
    out_web = report_dir / "output.svg"
    out_web.write_text(svg_web, encoding="utf-8")

    svg_readme = transform_wordcloud(badge_dic, preset="readme")
    out_readme = report_dir / "output_readme.svg"
    out_readme.write_text(svg_readme, encoding="utf-8")

    print(f"✓ Step 3 done — SVGs generated:")
    print(f"  • Web full-view (max space, 1400×900): file://{out_web}")
    print(f"  • README card  (standard, 920×540):   file://{out_readme}\n")

    # Step 4 — CSV reports summary
    out_csv = report_dir / "resolved.csv"
    if out_csv.exists():
        print(f"✓ Resolved badges CSV: file://{out_csv.resolve()}")
    filtered_csv = report_dir / "filtered.csv"
    if filtered_csv.exists():
        print(f"✓ Filtered/Noise packages CSV: file://{filtered_csv.resolve()}")
    unnorm_csv = report_dir / "unnormalized.csv"
    if unnorm_csv.exists():
        print(f"✓ Unnormalized packages CSV: file://{unnorm_csv.resolve()}")
    failed_csv = report_dir / "failed_icons.csv"
    if failed_csv.exists():
        print(f"✓ Failed icon lookups CSV: file://{failed_csv.resolve()}")
    print(f"\nRun artifacts: file://{report_dir.resolve()}\n")


if __name__ == "__main__":
    asyncio.run(run())