
from pathlib import Path 
import csv 
import logging 
from typing import Union

from app.reporting.csv import write_csv_rows


log = logging.getLogger(__name__)


class DepOpsLogger:
    """Optional CSV writer for CLI/debug runs. Web runs persist to MongoDB."""

    def __init__(self, root: Union[str, Path]):
        self.root = Path(root)
        self.output_path = self.root / "resolved.csv"
        self.resolve_metrics_path = self.root / "resolution_metrics.csv"
        self.validate_failures_path = self.root / "validation_failures.csv"
        self.failed_icons_path = self.root / "failed_icons.csv"

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

