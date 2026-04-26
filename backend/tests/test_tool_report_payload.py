import base64
import json
import unittest
import urllib.parse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.tool_service import ToolService


class ToolReportPayloadTest(unittest.TestCase):
    def test_embed_report_url_contains_type_and_data(self):
        payload = {"city": "南京", "score": 1.87}
        url = ToolService._build_embed_report_url("congestion", payload)
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)

        self.assertEqual(parsed.path, "/embed/report")
        self.assertEqual(query.get("type", [""])[0], "congestion")
        self.assertTrue(query.get("data", [""])[0])

    def test_embed_report_url_payload_roundtrip(self):
        payload = {"origin": "南京南站", "destination": "夫子庙", "duration_min": 19}
        url = ToolService._build_embed_report_url("route", payload)
        data = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("data", [""])[0]

        normalized = data.replace("-", "+").replace("_", "/")
        padded = normalized + "=" * ((4 - len(normalized) % 4) % 4)
        restored = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))

        self.assertEqual(restored["origin"], "南京南站")
        self.assertEqual(restored["duration_min"], 19)

    def test_iframe_result_schema(self):
        result = ToolService._build_iframe_result(
            tool_name="congestion_check",
            tool_label="城市拥堵体检",
            report_type="congestion",
            payload={"city": "南京"},
            text_data="已完成拥堵体检。"
        )
        body = json.loads(result)

        self.assertEqual(body["display_type"], "iframe_report")
        self.assertEqual(body["tool_name"], "congestion_check")
        self.assertEqual(body["tool_label"], "城市拥堵体检")
        self.assertIn("/embed/report?", body["iframe_url"])
        self.assertIn("text_data", body)


if __name__ == "__main__":
    unittest.main()
