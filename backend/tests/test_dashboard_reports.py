import unittest
from datetime import datetime
from unittest.mock import patch

from app import main


class DashboardReportTests(unittest.TestCase):
    def test_each_report_only_runs_its_queries(self):
        period = {
            "since": datetime(2026, 1, 1),
            "until": datetime(2026, 1, 8),
            "days": 7,
        }
        expected_queries = {
            "overview": 4,
            "trends": 4,
            "drives": 3,
            "charging": 5,
            "efficiency": 4,
            "battery": 3,
            "locations": 3,
            "vehicle": 1,
            "all": 18,
        }
        with (
            patch.object(main, "_cars", return_value=[{"id": 1}]),
            patch.object(main, "_period", return_value=period),
            patch.object(main, "fetch_one", return_value={}) as one,
            patch.object(main, "fetch_all", return_value=[]) as all_rows,
            patch.object(main, "today_energy", return_value={"points": []}) as energy,
        ):
            for report, expected in expected_queries.items():
                with self.subTest(report=report):
                    one.reset_mock()
                    all_rows.reset_mock()
                    energy.reset_mock()
                    result = main.dashboard(1, days=7, start=None, end=None, report=report)
                    self.assertEqual(one.call_count + all_rows.call_count, expected)
                    self.assertEqual(energy.call_count, int(report == "all"))
                    self.assertEqual(result["today_energy"], {"points": []} if report == "all" else None)
                    if report == "overview":
                        self.assertEqual(result["recent_drives"], [])
                        self.assertEqual(result["locations"]["routes"], [])


if __name__ == "__main__":
    unittest.main()
