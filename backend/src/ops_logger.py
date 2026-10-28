
from pathlib import Path 
import csv 
import logging 
from typing import Union, Sequence


log = logging.getLogger(__name__)


def write_csv_rows(filepath: Union[str, Path], fieldnames: Sequence[str], rows: Sequence[dict]) -> Path:
    out_path = Path(filepath)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)
    return out_path


class DepOpsLogger:

    def __init__(   
        self,
        output_path: str = "output/output.csv",
        resolve_metrics_path: str = "output/resolution_metrics.csv",
        validate_failures_path: str = "output/validation_failures.csv",
        failed_icons_path: str = "output/failed_icons.csv"
    ):
        self.output_path: str = output_path
        self.resolve_metrics_path = resolve_metrics_path
        self.validate_failures_path = validate_failures_path
        self.failed_icons_path = failed_icons_path
    

    def export_output_csv(
        self,
        badge_items: list[tuple[str, str, int]],
        resolved_methods: dict = None,
        resolved_urls: dict = None,
    ) -> Path:
        out_path = Path(self.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_methods = resolved_methods or {}
        resolved_urls = resolved_urls or {}
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["technology", "count", "resolution_method", "source_url"])
            for norm_name, _, count in sorted(badge_items, key=lambda x: x[2], reverse=True):
                method = resolved_methods.get(norm_name, "unknown")
                source_url = resolved_urls.get(norm_name, "")
                writer.writerow([norm_name, count, method, source_url])
        log.info("✓ Exported %d resolved icons to %s", len(badge_items), out_path)
        return out_path

    def export_audit_html(
        self,
        badge_items: list[tuple[str, str, int]],
        resolved_methods: dict = None,
        resolved_urls: dict = None,
        filepath: str = "icon_audit.html",
    ) -> Path:
        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_methods = resolved_methods or {}
        resolved_urls = resolved_urls or {}

        rows_html = []
        for norm_name, icon_uri, count in sorted(badge_items, key=lambda x: x[2], reverse=True):
            method = resolved_methods.get(norm_name, "unknown")
            source_url = resolved_urls.get(norm_name, "")
            link_html = (
                f'<a href="{source_url}" target="_blank" class="url-link">{source_url}</a>'
                if source_url and source_url.startswith("http")
                else f'<span class="url-text">{source_url or "—"}</span>'
            )
            method_badge = f'<span class="badge badge-{method}">{method}</span>'

            rows_html.append(
                f'<tr>'
                f'<td class="icon-cell"><img class="icon-preview" src="{icon_uri}" alt="{norm_name}" /></td>'
                f'<td><strong>{norm_name}</strong></td>'
                f'<td>{count}</td>'
                f'<td>{method_badge}</td>'
                f'<td>{link_html}</td>'
                f'</tr>'
            )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Logo Resolution Audit</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }}
    h1 {{ margin-bottom: 6px; font-size: 24px; }}
    p {{ color: #94a3b8; margin-top: 0; font-size: 14px; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #334155; font-size: 13px; }}
    th {{ background: #0f172a; color: #38bdf8; font-weight: 600; text-transform: uppercase; font-size: 11px; }}
    tr:hover {{ background: #283548; }}
    .icon-cell {{ width: 44px; text-align: center; }}
    .icon-preview {{ width: 32px; height: 32px; object-fit: contain; background: #0f172a; border-radius: 6px; padding: 3px; border: 1px solid #475569; }}
    .badge {{ display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 11px; font-weight: 500; background: #334155; color: #e2e8f0; }}
    .badge-cdn_catalog {{ background: #065f46; color: #34d399; }}
    .badge-db_cache {{ background: #1e3a8a; color: #60a5fa; }}
    .badge-github_opengraph {{ background: #7c2d12; color: #fdba74; }}
    .badge-homepage_favicon {{ background: #581c87; color: #c084fc; }}
    .badge-github_repo_probe {{ background: #831843; color: #f472b6; }}
    .badge-github_org_avatar {{ background: #134e4a; color: #5eead4; }}
    .url-link {{ color: #38bdf8; text-decoration: none; word-break: break-all; font-family: monospace; font-size: 12px; }}
    .url-link:hover {{ text-decoration: underline; }}
    .url-text {{ color: #64748b; font-family: monospace; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>Resolved Icon Mappings Audit</h1>
  <p>Total resolved icons: <strong>{len(badge_items)}</strong>. Inspect icons to verify they match the actual technology brand.</p>
  <table>
    <thead>
      <tr>
        <th class="icon-cell">Icon</th>
        <th>Technology</th>
        <th>Count</th>
        <th>Resolution Method</th>
        <th>Source / Mapped URL</th>
      </tr>
    </thead>
    <tbody>
      {"".join(rows_html)}
    </tbody>
  </table>
</body>
</html>"""

        with out_path.open("w", encoding="utf-8") as f:
            f.write(html_content)
        log.info("✓ Exported visual icon audit report to %s", out_path)
        return out_path

    def export_resolution_metrics_csv(self, recovery_stats: dict = None, failed_icons = None) -> Path:
        out_path = Path(self.resolve_metrics_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        recovery_stats = recovery_stats or {}
        failed_icons = failed_icons or []
        total_resolved = sum(recovery_stats.values())
        failed_count = len(failed_icons)
        total_attempted = total_resolved + failed_count
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["method", "resolved_count", "percentage"])
            for method, count in getattr(recovery_stats, "most_common", lambda: recovery_stats.items())():
                pct = round((count / total_attempted * 100), 2) if total_attempted else 0.0
                writer.writerow([method, count, f"{pct}%"])
            if failed_count > 0:
                pct = round((failed_count / total_attempted * 100), 2) if total_attempted else 0.0
                writer.writerow(["unresolved", failed_count, f"{pct}%"])
        log.info("✓ Exported resolution metrics to %s", out_path)
        return out_path

    def export_validation_failures_csv(self, validation_failures = None) -> Path:
        validation_failures = validation_failures or []
        out_path = write_csv_rows(self.validate_failures_path, ["url", "reason", "size_bytes"], validation_failures)
        log.info("✓ Exported %d validation failure records to %s", len(validation_failures), out_path)
        return out_path

    def export_failed_icons_csv(self, failed_icons = None) -> Path:
        failed_icons = failed_icons or []
        sorted_failures = sorted(failed_icons, key=lambda x: x.get("count", 0), reverse=True)
        out_path = write_csv_rows(
            self.failed_icons_path,
            ["norm_name", "raw_name", "dep_origin", "count", "slug_tried", "reason"],
            sorted_failures,
        )
        log.info("✓ Exported %d failed icon records to %s", len(failed_icons), out_path)
        return out_path

