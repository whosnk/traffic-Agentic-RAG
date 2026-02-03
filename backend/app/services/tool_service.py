# app/services/tool_service.py 完整替换

import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class ToolService:
    @staticmethod
    async def get_route_plan(origin_name: str, destination_name: str, mode: str = "driving"):
        """调用高德地图路径规划（支持驾车、步行、公交/地铁）"""
        api_key = settings.AMAP_KEY
        if not api_key: return "❌ 未配置地图 API Key"

        async with httpx.AsyncClient() as client:
            try:
                # 1. 地理编码：地名 -> 坐标 (所有模式都需要坐标)
                geo_url = "https://restapi.amap.com/v3/geocode/geo"
                r_o = await client.get(geo_url, params={"key": api_key, "address": origin_name})
                r_d = await client.get(geo_url, params={"key": api_key, "address": destination_name})

                if not r_o.json().get('geocodes') or not r_d.json().get('geocodes'):
                    return "找不到对应的地点，请确保地名输入正确。"

                origin_coord = r_o.json()['geocodes'][0]['location']
                dest_coord = r_d.json()['geocodes'][0]['location']
                city_code = r_o.json()['geocodes'][0]['adcode'][:4]  # 公交接口需要城市代码

                # 2. 根据模式选择接口
                res_msg = ""
                if mode == "transit":
                    # 公交/地铁接口
                    url = "https://restapi.amap.com/v3/direction/transit/integrated"
                    resp = await client.get(url, params={
                        "key": api_key, "origin": origin_coord, "destination": dest_coord, "city": city_code
                    })
                    data = resp.json()
                    if data['status'] == '1' and data['route']['transits']:
                        plan = data['route']['transits'][0]  # 取第一条推荐方案
                        res_msg = f"🚇 **为您规划公交/地铁路线：**\n\n"
                        res_msg += f"- 💰 票价：**{plan.get('cost', '未知')}** 元\n"
                        res_msg += f"- ⏱️ 预计耗时：**{round(int(plan['duration']) / 60, 0)}** 分钟\n"
                        res_msg += f"- 🚶 步行距离：**{plan['walking_distance']}** 米\n\n**换乘方案：**\n"

                        for seg in plan['segments']:
                            if seg.get('bus') and seg['bus']['buslines']:
                                line = seg['bus']['buslines'][0]
                                res_msg += f"> 🚌 乘坐 **{line['name']}** ({line['departure_stop']['name']} → {line['arrival_stop']['name']})\n"
                            if seg.get('walking'):
                                res_msg += f"> 🚶 步行约 {seg['walking']['distance']} 米\n"
                    else:
                        return "未找到合适的公交/地铁方案。"

                elif mode == "walking":
                    # 步行接口
                    url = "https://restapi.amap.com/v3/direction/walking"
                    resp = await client.get(url,
                                            params={"key": api_key, "origin": origin_coord, "destination": dest_coord})
                    data = resp.json()
                    if data['status'] == '1':
                        route = data['route']['paths'][0]
                        res_msg = f"🚶 **为您规划步行路线：**\n\n"
                        res_msg += f"- 📏 总距离：**{round(int(route['distance']) / 1000, 2)}** 公里\n"
                        res_msg += f"- ⏱️ 预计耗时：**{round(int(route['duration']) / 60, 0)}** 分钟\n\n**步行指引：**\n"
                        for i, step in enumerate(route['steps'][:8]):
                            res_msg += f"{i + 1}. {step['instruction']}\n"

                else:
                    # 默认：驾车接口
                    url = "https://restapi.amap.com/v3/direction/driving"
                    resp = await client.get(url,
                                            params={"key": api_key, "origin": origin_coord, "destination": dest_coord})
                    data = resp.json()
                    if data['status'] == '1':
                        route = data['route']['paths'][0]
                        res_msg = f"🚗 **为您规划驾车路线：**\n\n"
                        res_msg += f"- 📏 总里程：**{round(int(route['distance']) / 1000, 2)}** 公里\n"
                        res_msg += f"- ⏱️ 预计耗时：**{round(int(route['duration']) / 60, 0)}** 分钟\n\n**行驶建议：**\n"
                        for i, step in enumerate(route['steps'][:8]):
                            res_msg += f"{i + 1}. {step['instruction']}\n"

                res_msg += f"\n\n*温馨提示：导航数据由高德地图实时提供，请注意出行安全。*"
                return res_msg

            except Exception as e:
                logger.error(f"地图插件报错: {e}")
                return f"调用地图插件出错: {str(e)}"