import csv

from app.reporting.ops import DepOpsLogger


class TestRunReportWriter:
    def test_output_csv_includes_source_url(self, tmp_path):
        logger = DepOpsLogger(tmp_path)
        badge_items = [("FastAPI", "data:image/svg+xml;base64,AAA", 5)]
        methods = {"FastAPI": "cdn_catalog"}
        urls = {"FastAPI": "https://cdn.simpleicons.org/fastapi"}
        csv_path = logger.export_output_csv(badge_items, methods, urls)

        assert csv_path == tmp_path / "resolved.csv"
        with csv_path.open() as f:
            reader = list(csv.reader(f))
            assert reader[0] == ["technology", "count", "resolution_method", "source_url"]
            assert reader[1] == ["FastAPI", "5", "cdn_catalog", "https://cdn.simpleicons.org/fastapi"]

    def test_all_reports_stay_inside_run_root(self, tmp_path):
        logger = DepOpsLogger(tmp_path)
        badge_items = [("FastAPI", "data:image/svg+xml;base64,AAA", 5)]

        logger.export_output_csv(badge_items, {"FastAPI": "cdn_catalog"}, {})
        logger.export_failed_icons_csv(
            [{"norm_name": "Nope", "raw_name": "nope", "dep_origin": "ts", "count": 1, "slug_tried": "nope", "reason": "no_icon_found"}]
        )
        logger.export_resolution_metrics_csv({"cdn_catalog": 1}, [])
        logger.export_validation_failures_csv([{"url": "https://x.test/a.svg", "reason": "bad", "size_bytes": 10}])

        assert {p.name for p in tmp_path.iterdir()} == {
            "resolved.csv",
            "failed_icons.csv",
            "resolution_metrics.csv",
            "validation_failures.csv",
        }
