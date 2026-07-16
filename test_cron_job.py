import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd

from cron_job import build_fallback_report, filter_candidates, normalize_cbas_data
from services.notification import _split_telegram_message, send_telegram_message


class CronJobDataPipelineTest(unittest.TestCase):
    def test_normalize_cbas_data_maps_required_fields_and_dates(self):
        raw = pd.DataFrame(
            [
                {
                    "債券代號": "30455 ",
                    "標的債券": "台灣大五",
                    "可轉債市價": "105.7",
                    "溢(折)價率": "3.7",
                    "餘額比例": "1.0",
                    "轉換價值": "1.02",
                    "最新賣回日": "2027-07-16",
                    "發行日期": "2025-07-16",
                }
            ]
        )

        df = normalize_cbas_data(raw, today=datetime(2026, 7, 16))

        self.assertEqual(df.loc[0, "代號"], "30455")
        self.assertEqual(df.loc[0, "股票代號"], "3045")
        self.assertEqual(df.loc[0, "名稱"], "台灣大五")
        self.assertAlmostEqual(df.loc[0, "餘額"], 100.0)
        self.assertAlmostEqual(df.loc[0, "轉換價值"], 102.0)
        self.assertEqual(df.loc[0, "上市天數"], 365)
        self.assertEqual(df.loc[0, "距離賣回日(天)"], 365)

    def test_filter_candidates_applies_strategy_config(self):
        df = pd.DataFrame(
            [
                {"CB市價": 105, "溢/折價": 4, "餘額": 95, "轉換價值": 101},
                {"CB市價": 140, "溢/折價": 4, "餘額": 95, "轉換價值": 101},
            ]
        )
        config = {
            "filter_price_min": 100,
            "filter_price_max": 120,
            "filter_prem_min": 0,
            "filter_prem_max": 15,
            "filter_ratio_min": 90,
            "filter_parity_min": 90,
            "filter_parity_max": 110,
        }

        filtered = filter_candidates(df, config)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered.iloc[0]["CB市價"], 105)

    def test_build_fallback_report_contains_ranked_candidates(self):
        candidates = pd.DataFrame(
            [
                {
                    "名稱": "台灣大五",
                    "代號": "30455",
                    "R值": 1,
                    "P值": 7,
                    "策略標籤": "鄭大精選",
                    "CB市價": 105.7,
                    "溢/折價": 3.7,
                    "轉換價值": 102.0,
                    "餘額": 100.0,
                    "警示": "",
                }
            ]
        )

        report = build_fallback_report(candidates)

        self.assertIn("今日 CBAS 自動掃描摘要", report)
        self.assertIn("台灣大五(30455)", report)
        self.assertIn("R1 / P7", report)
        self.assertIn("不構成投資建議", report)

    @patch("services.notification.requests.post")
    def test_send_telegram_message_reports_success(self, post):
        post.return_value = Mock(ok=True, status_code=200, text="")

        ok, message = send_telegram_message("token", "chat", "hello")

        self.assertTrue(ok)
        self.assertEqual(message, "Telegram message sent (1 part)")
        post.assert_called_once()

    @patch("services.notification.requests.post")
    def test_send_telegram_message_reports_api_error(self, post):
        post.return_value = Mock(ok=False, status_code=401, text="invalid token")

        ok, message = send_telegram_message("token", "chat", "hello")

        self.assertFalse(ok)
        self.assertIn("401", message)
        self.assertIn("invalid token", message)

    def test_send_telegram_message_requires_chat_id(self):
        ok, message = send_telegram_message("token", "", "hello")

        self.assertFalse(ok)
        self.assertEqual(message, "TELEGRAM_CHAT_ID is empty")

    def test_split_telegram_message_respects_limit(self):
        chunks = _split_telegram_message("a" * 5000, limit=4096)

        self.assertEqual(len(chunks), 2)
        self.assertLessEqual(max(len(chunk) for chunk in chunks), 4096)


if __name__ == "__main__":
    unittest.main()
