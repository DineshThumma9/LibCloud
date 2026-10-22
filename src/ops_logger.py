
from pathlib import Path 
import csv 
import logging 


log = logging.getLogger(__name__)

class DepOpsLogger:

    def __init__(   
        self,
        output_path: str = "output.csv",
        resolve_metrics_path: str = "resolution_metrics.csv",
        validate_failures_path: str = "validation_failures.csv",
        failed_icons_path: str = "failed_icons.csv"
    ):
        self.output_path: str = output_path
        self.resolve_metrics_path = resolve_metrics_path
        self.validate_failures_path = validate_failures_path
        self.failed_icons_path = failed_icons_path
    

    def export_output_csv(self, badge_items: list[tuple[str, str, int]], resolved_methods: dict = None) -> Path:
        out_path = Path(self.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_methods = resolved_methods or {}
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["technology", "count", "resolution_method"])
            for norm_name, _, count in sorted(badge_items, key=lambda x: x[2], reverse=True):
                method = resolved_methods.get(norm_name, "unknown")
                writer.writerow([norm_name, count, method])
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
        out_path = Path(self.validate_failures_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        validation_failures = validation_failures or []
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "reason", "size_bytes"])
            writer.writeheader()
            writer.writerows(validation_failures)
        log.info("✓ Exported %d validation failure records to %s", len(validation_failures), out_path)
        return out_path

    def export_failed_icons_csv(self, failed_icons = None) -> Path:
        out_path = Path(self.failed_icons_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        failed_icons = failed_icons or []
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["norm_name", "raw_name", "dep_origin", "count", "slug_tried", "reason"]
            )
            writer.writeheader()
            sorted_failures = sorted(failed_icons, key=lambda x: x.get("count", 0), reverse=True)
            writer.writerows(sorted_failures)
        log.info("✓ Exported %d failed icon records to %s", len(failed_icons), out_path)
        return out_path

