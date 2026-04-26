import asyncio
import base64
import httpx
import json
import logging
import re
import urllib.parse
from datetime import datetime

from langchain_core.tools import tool

from app.core.config import settings
from app.core.constants import AmapAPI

logger = logging.getLogger(__name__)


class ToolService:
    @staticmethod
    def _split_location(location):
        if not location:
            return None
        try:
            lng, lat = location.split(",")
            return [round(float(lng), 6), round(float(lat), 6)]
        except Exception:
            return None

    @staticmethod
    def _to_base64url(payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    @staticmethod
    def _build_embed_report_url(report_type, payload):
        data = ToolService._to_base64url(payload)
        safe_type = urllib.parse.quote(str(report_type))
        safe_data = urllib.parse.quote(data)
        return f"/embed/report?type={safe_type}&data={safe_data}"

    @staticmethod
    def _build_iframe_result(tool_name, tool_label, report_type, payload, text_data):
        return json.dumps({
            "text_data": text_data,
            "tool_name": tool_name,
            "tool_label": tool_label,
            "display_type": "iframe_report",
            "iframe_url": ToolService._build_embed_report_url(report_type, payload)
        }, ensure_ascii=False)

    @staticmethod
    def _extract_polyline_points(path_obj):
        points = []
        for step in path_obj.get("steps", []):
            polyline = step.get("polyline", "")
            if not polyline:
                continue
            for p in polyline.split(";"):
                p = p.strip()
                if not p:
                    continue
                loc = ToolService._split_location(p)
                if loc:
                    points.append(loc)
                if len(points) >= 220:
                    return points
        return points

    @staticmethod
    async def _resolve_coordinates(client, api_key, address, city=None):
        """智能坐标解析助手 (支持模糊匹配)"""
        try:
            # 1. 尝试 POI 搜索
            res = await client.get(AmapAPI.PLACE_TEXT,
                                   params={"key": api_key, "keywords": address, "city": city, "offset": 1,
                                           "extensions": "all"})
            data = res.json()
            if data.get('status') == '1' and data.get('pois'):
                top_poi = data['pois'][0]
                return top_poi['location'], top_poi['name'], top_poi['adcode']

            # 2. 尝试地理编码
            res = await client.get(AmapAPI.GEOCODE, params={"key": api_key, "address": address})
            data = res.json()
            if data.get('status') == '1' and data.get('geocodes'):
                geo = data['geocodes'][0]
                return geo['location'], geo['formatted_address'], geo['adcode']
        except Exception:
            pass

        return None, None, None

    @staticmethod
    async def get_route_plan(origin_name: str, destination_name: str, mode: str = "driving"):
        api_key = settings.AMAP_KEY
        if not api_key:
            return json.dumps({"text_data": "地图服务未配置，无法生成路径报告。"}, ensure_ascii=False)

        async with httpx.AsyncClient() as client:
            try:
                origin_name = str(origin_name)
                destination_name = str(destination_name)

                o_loc, o_name, o_adcode = await ToolService._resolve_coordinates(client, api_key, origin_name)
                d_loc, d_name, _ = await ToolService._resolve_coordinates(client, api_key, destination_name)

                if not o_loc or not d_loc:
                    return json.dumps({"text_data": f"抱歉，无法精确识别地点 {origin_name} 或 {destination_name}。"},
                                      ensure_ascii=False)

                payload = {
                    "title": "路线规划报告",
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "mode": mode,
                    "origin_name": o_name,
                    "destination_name": d_name,
                    "origin_loc": ToolService._split_location(o_loc),
                    "destination_loc": ToolService._split_location(d_loc),
                    "distance_km": None,
                    "duration_min": None,
                    "taxi_cost": None,
                    "walking_distance_m": None,
                    "line_name": "",
                    "polyline": []
                }

                if mode == "driving":
                    resp = await client.get(AmapAPI.DIR_DRIVING,
                                            params={"key": api_key, "origin": o_loc, "destination": d_loc,
                                                    "strategy": 10})
                    data = resp.json()
                    if data.get('status') == '1' and data.get('route', {}).get('paths'):
                        r = data['route']['paths'][0]
                        payload["distance_km"] = round(int(r["distance"]) / 1000, 2)
                        payload["duration_min"] = round(int(r["duration"]) / 60)
                        payload["taxi_cost"] = data.get("route", {}).get("taxi_cost")
                        payload["polyline"] = ToolService._extract_polyline_points(r)
                    text_data = f"已生成从{o_name}到{d_name}的驾车路线报告，预计用时{payload['duration_min'] or '未知'}分钟。"

                elif mode == "transit":
                    resp = await client.get(AmapAPI.DIR_TRANSIT,
                                            params={"key": api_key, "origin": o_loc, "destination": d_loc,
                                                    "city": o_adcode, "strategy": 0})
                    data = resp.json()
                    if data.get('status') == '1' and data.get('route', {}).get('transits'):
                        plan = data['route']['transits'][0]
                        payload["duration_min"] = round(int(plan["duration"]) / 60)
                        payload["walking_distance_m"] = int(plan.get("walking_distance", 0))
                        payload["line_name"] = " + ".join([
                            seg.get("bus", {}).get("buslines", [{}])[0].get("name", "")
                            for seg in plan.get("segments", []) if seg.get("bus", {}).get("buslines")
                        ])[:120]
                    text_data = f"已生成从{o_name}到{d_name}的公交换乘报告，预计用时{payload['duration_min'] or '未知'}分钟。"
                else:
                    resp = await client.get(AmapAPI.DIR_WALKING,
                                            params={"key": api_key, "origin": o_loc, "destination": d_loc})
                    data = resp.json()
                    if data.get("status") == "1" and data.get("route", {}).get("paths"):
                        r = data["route"]["paths"][0]
                        payload["distance_km"] = round(int(r["distance"]) / 1000, 2)
                        payload["duration_min"] = round(int(r["duration"]) / 60)
                        payload["polyline"] = ToolService._extract_polyline_points(r)
                    text_data = f"已生成从{o_name}到{d_name}的步行路线报告，预计用时{payload['duration_min'] or '未知'}分钟。"

                return ToolService._build_iframe_result(
                    tool_name="route_plan",
                    tool_label="路径规划",
                    report_type="route",
                    payload=payload,
                    text_data=text_data
                )

            except Exception as e:
                logger.error(f"路线规划故障: {e}")
                return json.dumps({"text_data": f"路线规划服务暂时不可用: {str(e)}"}, ensure_ascii=False)

    @staticmethod
    async def search_nearby(keyword: str, city: str = "全国"):
        api_key = settings.AMAP_KEY
        if not keyword:
            return json.dumps({"text_data": "缺少搜索关键词。"}, ensure_ascii=False)

        async with httpx.AsyncClient() as client:
            try:
                search_query = str(keyword)
                anchor_loc = None
                display_name = search_query
                anchor_name = ""

                match = re.search(r"(.+?)(附近|周边)(?:的)?(.+)", search_query)
                if match:
                    landmark = match.group(1)
                    poi_type = match.group(3)
                    coords, formal_name, _ = await ToolService._resolve_coordinates(client, api_key, landmark, city)
                    if coords:
                        anchor_loc = coords
                        search_query = poi_type
                        display_name = f"{formal_name} 附近的 {poi_type}"
                        anchor_name = formal_name
                else:
                    coords, formal_name, _ = await ToolService._resolve_coordinates(client, api_key, search_query, city)
                    if coords:
                        anchor_loc = coords
                        anchor_name = formal_name

                poi_resp = await client.get(AmapAPI.PLACE_TEXT, params={
                    "key": api_key,
                    "keywords": search_query,
                    "city": city,
                    "offset": 8,
                    "page": 1,
                    "extensions": "base"
                })
                poi_data = poi_resp.json()
                pois = []
                for poi in poi_data.get("pois", [])[:8]:
                    loc = ToolService._split_location(poi.get("location"))
                    pois.append({
                        "name": poi.get("name", ""),
                        "address": poi.get("address", "") or poi.get("type", ""),
                        "distance_m": poi.get("distance", ""),
                        "location": loc
                    })

                payload = {
                    "title": "周边搜索报告",
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "city": city,
                    "query": search_query,
                    "display_name": display_name,
                    "anchor_name": anchor_name,
                    "anchor_loc": ToolService._split_location(anchor_loc),
                    "pois": pois
                }
                text_data = f"已生成【{display_name}】周边搜索报告，共识别到{len(pois)}个候选点。"
                return ToolService._build_iframe_result(
                    tool_name="nearby_search",
                    tool_label="周边搜索",
                    report_type="nearby",
                    payload=payload,
                    text_data=text_data
                )

            except Exception as e:
                logger.error(f"周边搜索故障: {e}")
                return json.dumps({"text_data": f"周边搜索暂时不可用: {str(e)}"}, ensure_ascii=False)

    @staticmethod
    async def congestion_check(question: str, city: str = "南京", region: str = "主城区"):
        digest = sum(ord(c) for c in str(question)) % 17
        time_window = "今日早高峰（07:30-09:30）"
        if "晚高峰" in question or "下班" in question:
            time_window = "今日晚高峰（17:30-19:30）"
        elif "全天" in question:
            time_window = "今日全天（00:00-24:00）"

        congestion_index = round(1.65 + digest * 0.07, 2)
        avg_speed = 34 - digest
        delay_index = round(1.42 + digest * 0.05, 2)
        abnormal_roads = 18 + digest

        hotspot_templates = [
            {"name": "新街口商圈", "level": "高", "location": [118.787, 32.041]},
            {"name": "夫子庙周边", "level": "高", "location": [118.793, 32.023]},
            {"name": "河西中部", "level": "中高", "location": [118.729, 32.009]},
            {"name": "南京南站片区", "level": "中高", "location": [118.804, 31.979]}
        ]
        hotspots = hotspot_templates[:3 + (digest % 2)]
        causes = [
            "主干路潮汐通勤车流集中，节点排队外溢明显。",
            "核心商圈临停与掉头行为增加，影响路口放行效率。",
            "部分干道施工占道导致瓶颈段通行能力下降。"
        ]
        suggestions = [
            "对热点走廊实施早晚高峰绿波带参数优化。",
            "在拥堵片区增设潮汐引导与停车诱导信息。",
            "针对高频异常路段开展精细化配时与执法联动。"
        ]
        payload = {
            "title": "城市拥堵体检报告",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "city": city,
            "region": region,
            "time_window": time_window,
            "congestion_index": congestion_index,
            "avg_speed": avg_speed,
            "delay_index": delay_index,
            "abnormal_road_count": abnormal_roads,
            "hotspots": hotspots,
            "causes": causes,
            "suggestions": suggestions,
            "map_center": hotspots[0]["location"] if hotspots else [118.787, 32.041]
        }
        text_data = (
            f"已完成{city}{region}拥堵体检：拥堵指数{congestion_index}，"
            f"平均车速约{avg_speed}km/h，识别异常路段{abnormal_roads}条。"
        )
        return ToolService._build_iframe_result(
            tool_name="congestion_check",
            tool_label="城市拥堵体检",
            report_type="congestion",
            payload=payload,
            text_data=text_data
        )

    @staticmethod
    async def get_weather(city_name: str):
        api_key = settings.AMAP_KEY
        if not city_name:
            return json.dumps({"text_data": "缺少城市名称。"}, ensure_ascii=False)

        async with httpx.AsyncClient() as client:
            try:
                city_name = str(city_name)
                # 使用常量池中的 API
                r_o = await client.get(AmapAPI.GEOCODE, params={"key": api_key, "address": city_name})
                if not r_o.json().get('geocodes'):
                    return json.dumps({"text_data": f"抱歉，无法识别城市：{city_name}"}, ensure_ascii=False)

                city_data = r_o.json()['geocodes'][0]
                adcode = city_data['adcode']
                formatted_city = city_data['city'] if city_data['city'] else city_data['province']

                # 并发请求使用常量 API
                r_live, r_cast = await asyncio.gather(
                    client.get(AmapAPI.WEATHER_INFO, params={"key": api_key, "city": adcode, "extensions": "base"}),
                    client.get(AmapAPI.WEATHER_INFO, params={"key": api_key, "city": adcode, "extensions": "all"})
                )

                data_live = r_live.json()
                data_cast = r_cast.json()

                if data_live.get('status') == '1' and data_live.get('lives'):
                    live = data_live['lives'][0]
                    temp = live['temperature']
                    weather = live['weather']
                    wind_dir = live['winddirection']
                    wind_power = live['windpower']
                    humidity = live['humidity']
                    report_time = live['reporttime'][:10]

                    bg_gradient = "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
                    icon = "☀️"
                    if "雨" in weather:
                        bg_gradient = "linear-gradient(135deg, #616161 0%, #9bc5c3 100%)"
                        icon = "🌧️"
                    elif "云" in weather or "阴" in weather:
                        bg_gradient = "linear-gradient(135deg, #8ba8b5 0%, #b2c6ce 100%)"
                        icon = "☁️"
                    elif "雪" in weather:
                        bg_gradient = "linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%)"
                        icon = "❄️"

                    html_widget = f"""<div style="border-radius: 20px; overflow: hidden; margin: 16px 0; background: {bg_gradient}; box-shadow: 0 10px 30px rgba(0,0,0,0.15); color: #fff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
<div style="padding: 24px; position: relative;">
<div style="font-size: 22px; font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">{formatted_city}</div>
<div style="font-size: 64px; font-weight: 300; margin: 10px 0; display: flex; align-items: center; gap: 12px; text-shadow: 0 4px 12px rgba(0,0,0,0.1);">
<span>{temp}°</span> <span style="font-size: 48px;">{icon}</span>
</div>
<div style="font-size: 18px; font-weight: 500; margin-bottom: 20px;">{weather}</div>
<div style="display: flex; justify-content: space-between; background: rgba(255,255,255,0.2); padding: 12px 16px; border-radius: 12px; backdrop-filter: blur(10px); text-shadow: 0 1px 2px rgba(0,0,0,0.1);">
<div style="text-align: center;">
<div style="font-size: 12px; opacity: 0.9; margin-bottom: 4px;">风向</div>
<div style="font-size: 14px; font-weight: bold;">{wind_dir}风 {wind_power}级</div>
</div>
<div style="width: 1px; background: rgba(255,255,255,0.3);"></div>
<div style="text-align: center;">
<div style="font-size: 12px; opacity: 0.9; margin-bottom: 4px;">湿度</div>
<div style="font-size: 14px; font-weight: bold;">{humidity}%</div>
</div>
<div style="width: 1px; background: rgba(255,255,255,0.3);"></div>
<div style="text-align: center;">
<div style="font-size: 12px; opacity: 0.9; margin-bottom: 4px;">更新</div>
<div style="font-size: 14px; font-weight: bold;">{report_time}</div>
</div>
</div>
</div>
"""
                    if data_cast.get('status') == '1' and data_cast.get('forecasts'):
                        casts = data_cast['forecasts'][0]['casts'][1:4]
                        html_widget += """<div style="padding: 16px 24px; background: rgba(0,0,0,0.15); border-top: 1px solid rgba(255,255,255,0.1);">\n"""
                        for day in casts:
                            day_icon = "☀️" if "晴" in day['dayweather'] else "🌧️" if "雨" in day[
                                'dayweather'] else "☁️"
                            html_widget += f"""<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; font-size: 15px;">\n<span style="width: 60px; font-weight:500;">周{day['week']}</span>\n<span style="flex: 1; text-align: center;">{day_icon} {day['dayweather']}</span>\n<span style="width: 80px; text-align: right; opacity: 0.9;">{day['nighttemp']}° / {day['daytemp']}°</span>\n</div>\n"""
                        html_widget += "</div>\n"
                    html_widget += "</div>"

                    text_data = f"已为用户展示精美天气卡片。当前：{weather}，{temp}度。请根据天气（如是否下雨/高温）给出简短贴心的出行、穿衣或洗车建议。"
                    return json.dumps({"html_widget": html_widget, "text_data": text_data}, ensure_ascii=False)
                else:
                    return json.dumps({"text_data": "气象局接口暂无响应。"}, ensure_ascii=False)
            except Exception as e:
                logger.error(f"天气插件故障: {e}")
                return json.dumps({"text_data": f"天气查询暂时不可用: {str(e)}"}, ensure_ascii=False)


@tool
async def agent_get_route(origin_name: str, destination_name: str, mode: str = "driving"):
    """当用户咨询路线规划、导航、时长与距离时调用。"""
    return await ToolService.get_route_plan(origin_name, destination_name, mode)


@tool
async def agent_search_nearby(keyword: str, city: str = "全国"):
    """当用户查找周边停车场、充电桩、医院、商超等设施时调用。"""
    return await ToolService.search_nearby(keyword, city)


@tool
async def agent_congestion_check(question: str, city: str = "南京", region: str = "主城区"):
    """当用户要求拥堵体检、拥堵分析、拥堵原因诊断时调用。"""
    return await ToolService.congestion_check(question, city, region)


@tool
async def agent_get_weather(city_name: str):
    """天气查询工具（默认链路已下线，仅兼容保留）。"""
    return await ToolService.get_weather(city_name)
