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

    def test_ev_charge_plan_template(self):
        plan = ToolService._build_ev_charge_plan(
            distance_km=320,
            duration_min=250,
            polyline=[[118.1, 32.1], [119.1, 31.8], [120.1, 31.3]],
            current_soc=45,
            reserve_soc=20,
            style="经济"
        )

        self.assertEqual(plan["style"], "经济")
        self.assertGreaterEqual(plan["estimated_total_time_min"], 250)
        self.assertIn("charge_stops", plan)
        self.assertGreaterEqual(len(plan["charge_stops"]), 1)
        self.assertIn("estimated_cost", plan["charge_stops"][0])

    def test_real_charge_station_replaces_strategy_stop(self):
        plan = ToolService._build_ev_charge_plan(
            distance_km=320,
            duration_min=250,
            polyline=[[118.1, 32.1], [119.1, 31.8], [120.1, 31.3]],
            current_soc=45,
            reserve_soc=20,
            style="均衡"
        )
        stations = [[{
            "name": "沪宁高速阳澄湖服务区充电站",
            "address": "阳澄湖服务区",
            "location": [120.82, 31.42],
            "distance_m": "2300"
        }]]

        ToolService._attach_real_charge_stations(plan["charge_stops"], stations)

        self.assertEqual(plan["charge_stops"][0]["name"], "沪宁高速阳澄湖服务区充电站")
        self.assertEqual(plan["charge_stops"][0]["location"], [120.82, 31.42])
        self.assertEqual(plan["charge_stops"][0]["station_source"], "amap_poi")
        self.assertIn("阳澄湖服务区", plan["charge_stops"][0]["address"])

    def test_strategy_stop_kept_when_no_real_station(self):
        plan = ToolService._build_ev_charge_plan(
            distance_km=320,
            duration_min=250,
            polyline=[[118.1, 32.1], [119.1, 31.8], [120.1, 31.3]],
            current_soc=45,
            reserve_soc=20,
            style="均衡"
        )
        old_name = plan["charge_stops"][0]["name"]
        old_location = plan["charge_stops"][0]["location"]

        ToolService._attach_real_charge_stations(plan["charge_stops"], [[]])

        self.assertEqual(plan["charge_stops"][0]["name"], old_name)
        self.assertEqual(plan["charge_stops"][0]["location"], old_location)
        self.assertEqual(plan["charge_stops"][0]["station_source"], "strategy")

    def test_ev_simulation_events_include_drive_and_charge(self):
        plan = ToolService._build_ev_charge_plan(
            distance_km=320,
            duration_min=250,
            polyline=[[118.1, 32.1], [119.1, 31.8], [120.1, 31.3]],
            current_soc=45,
            reserve_soc=20,
            style="均衡"
        )
        events = ToolService._build_ev_simulation_events(
            origin_name="南京",
            destination_name="上海",
            distance_km=320,
            duration_min=250,
            current_soc=45,
            reserve_soc=20,
            charge_stops=plan["charge_stops"]
        )

        self.assertEqual(events[0]["type"], "drive")
        self.assertTrue(any(item["type"] == "charge" for item in events))
        self.assertEqual(events[-1]["to"], "上海")
        self.assertGreater(events[-1]["end_soc"], 0)

    def test_city_fallback_resolves_nanjing_and_shanghai(self):
        nanjing = ToolService._fallback_location("南京")
        shanghai = ToolService._fallback_location("上海")

        self.assertEqual(nanjing[1], "南京")
        self.assertEqual(shanghai[1], "上海")
        self.assertEqual(len(nanjing[0].split(",")), 2)

    def test_fallback_route_has_distance_and_polyline(self):
        route = ToolService._build_fallback_route(
            origin_loc="118.796877,32.060255",
            destination_loc="121.473667,31.230525"
        )

        self.assertGreater(route["distance_km"], 0)
        self.assertGreater(route["duration_min"], 0)
        self.assertGreater(len(route["polyline"]), 2)


if __name__ == "__main__":
    unittest.main()
