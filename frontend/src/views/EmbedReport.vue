<template>
  <div class="embed-page">
    <div class="panel">
      <div v-if="errorMsg" class="error-box">{{ errorMsg }}</div>

      <template v-else>
        <header class="report-header">
          <h2>{{ pageTitle }}</h2>
          <span class="time-text">{{ payload.generated_at || '-' }}</span>
        </header>

        <section v-if="reportType === 'congestion'" class="section">
          <div class="meta-grid">
            <div class="meta-item"><span>城市</span><strong>{{ payload.city || '-' }}</strong></div>
            <div class="meta-item"><span>区域</span><strong>{{ payload.region || '-' }}</strong></div>
            <div class="meta-item"><span>时段</span><strong>{{ payload.time_window || '-' }}</strong></div>
            <div class="meta-item"><span>生成时间</span><strong>{{ payload.generated_at || '-' }}</strong></div>
          </div>

          <div class="kpi-grid">
            <div class="kpi"><span>拥堵指数</span><strong>{{ payload.congestion_index ?? '-' }}</strong></div>
            <div class="kpi"><span>平均车速</span><strong>{{ payload.avg_speed ?? '-' }} km/h</strong></div>
            <div class="kpi"><span>延误指数</span><strong>{{ payload.delay_index ?? '-' }}</strong></div>
            <div class="kpi"><span>异常路段数</span><strong>{{ payload.abnormal_road_count ?? '-' }}</strong></div>
          </div>

          <div class="list-block">
            <h3>重点拥堵区域</h3>
            <ul>
              <li v-for="(item, idx) in payload.hotspots || []" :key="`hot-${idx}`">
                {{ item.name }}（等级：{{ item.level || '中' }}）
              </li>
            </ul>
          </div>

          <div class="list-block">
            <h3>拥堵成因分析</h3>
            <ul>
              <li v-for="(item, idx) in payload.causes || []" :key="`cause-${idx}`">{{ item }}</li>
            </ul>
          </div>

          <div class="list-block">
            <h3>初步治理建议</h3>
            <ul>
              <li v-for="(item, idx) in payload.suggestions || []" :key="`sg-${idx}`">{{ item }}</li>
            </ul>
          </div>
        </section>

        <section v-if="reportType === 'route'" class="section">
          <div class="meta-grid">
            <div class="meta-item"><span>起点</span><strong>{{ payload.origin_name || '-' }}</strong></div>
            <div class="meta-item"><span>终点</span><strong>{{ payload.destination_name || '-' }}</strong></div>
            <div class="meta-item"><span>方式</span><strong>{{ modeLabel }}</strong></div>
            <div class="meta-item"><span>生成时间</span><strong>{{ payload.generated_at || '-' }}</strong></div>
          </div>

          <div class="kpi-grid">
            <div class="kpi"><span>总距离</span><strong>{{ payload.distance_km ?? '-' }} km</strong></div>
            <div class="kpi"><span>预计耗时</span><strong>{{ payload.duration_min ?? '-' }} min</strong></div>
            <div class="kpi"><span>步行距离</span><strong>{{ payload.walking_distance_m ?? '-' }} m</strong></div>
            <div class="kpi"><span>打车预估</span><strong>{{ payload.taxi_cost ?? '-' }}</strong></div>
          </div>

          <div v-if="payload.line_name" class="list-block">
            <h3>推荐换乘</h3>
            <p>{{ payload.line_name }}</p>
          </div>
        </section>

        <section v-if="reportType === 'nearby'" class="section">
          <div class="meta-grid">
            <div class="meta-item"><span>城市</span><strong>{{ payload.city || '-' }}</strong></div>
            <div class="meta-item"><span>检索词</span><strong>{{ payload.query || '-' }}</strong></div>
            <div class="meta-item"><span>锚点</span><strong>{{ payload.anchor_name || '-' }}</strong></div>
            <div class="meta-item"><span>结果数</span><strong>{{ (payload.pois || []).length }}</strong></div>
          </div>

          <div class="list-block">
            <h3>候选点位</h3>
            <ul>
              <li v-for="(item, idx) in payload.pois || []" :key="`poi-${idx}`">
                {{ item.name }} · {{ item.address || '地址待补充' }}
                <span v-if="item.distance_m">（{{ item.distance_m }}m）</span>
              </li>
            </ul>
          </div>
        </section>

        <section class="section">
          <h3>地图画布</h3>
          <div ref="mapRef" class="map-box"></div>
          <div v-if="mapHint" class="map-hint">{{ mapHint }}</div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const reportType = ref('');
const payload = ref<any>({});
const errorMsg = ref('');
const mapHint = ref('');
const mapRef = ref<HTMLElement | null>(null);
let mapInstance: any = null;

const pageTitle = computed(() => {
  if (reportType.value === 'congestion') return payload.value.title || '城市拥堵体检报告';
  if (reportType.value === 'route') return payload.value.title || '路线规划报告';
  if (reportType.value === 'nearby') return payload.value.title || '周边搜索报告';
  return '报告页';
});

const modeLabel = computed(() => {
  const mode = String(payload.value.mode || 'driving');
  if (mode === 'transit') return '公交/地铁';
  if (mode === 'walking') return '步行';
  return '驾车';
});

const decodePayload = (raw: string) => {
  const normalized = raw.replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
  const text = new TextDecoder().decode(bytes);
  return JSON.parse(text);
};

const parseQuery = () => {
  try {
    const type = String(route.query.type || '').trim();
    const data = String(route.query.data || '').trim();
    if (!type || !data) {
      errorMsg.value = '报告参数缺失，请返回聊天页重新生成。';
      return;
    }
    reportType.value = type;
    payload.value = decodePayload(data);
    errorMsg.value = '';
  } catch (e) {
    errorMsg.value = '报告数据解析失败，请重新发起工具调用。';
  }
};

const loadAmap = async (key: string) => {
  if ((window as any).AMap) return;
  const securityCode = String(import.meta.env.VITE_AMAP_SECURITY_JS_CODE || '').trim();
  if (securityCode) {
    (window as any)._AMapSecurityConfig = { securityJsCode: securityCode };
  }
  await new Promise<void>((resolve, reject) => {
    const oldScript = document.getElementById('amap-sdk-loader');
    if (oldScript) {
      oldScript.addEventListener('load', () => resolve(), { once: true });
      oldScript.addEventListener('error', () => reject(new Error('load fail')), { once: true });
      return;
    }
    const script = document.createElement('script');
    script.id = 'amap-sdk-loader';
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}`;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('load fail'));
    document.body.appendChild(script);
  });
};

const collectMapElements = () => {
  const markers: any[] = [];
  const polylines: any[] = [];
  let center = payload.value.map_center || payload.value.anchor_loc || payload.value.origin_loc || [118.787, 32.041];

  if (reportType.value === 'congestion') {
    const hotspots = payload.value.hotspots || [];
    hotspots.forEach((h: any) => {
      if (h.location && h.location.length === 2) {
        markers.push({ position: h.location, title: h.name || '拥堵点' });
      }
    });
    if (hotspots.length && hotspots[0].location) center = hotspots[0].location;
  } else if (reportType.value === 'route') {
    if (payload.value.origin_loc) markers.push({ position: payload.value.origin_loc, title: payload.value.origin_name || '起点' });
    if (payload.value.destination_loc) markers.push({ position: payload.value.destination_loc, title: payload.value.destination_name || '终点' });
    if (Array.isArray(payload.value.polyline) && payload.value.polyline.length > 1) {
      polylines.push(payload.value.polyline);
    }
    if (payload.value.origin_loc) center = payload.value.origin_loc;
  } else if (reportType.value === 'nearby') {
    if (payload.value.anchor_loc) markers.push({ position: payload.value.anchor_loc, title: payload.value.anchor_name || '中心点' });
    (payload.value.pois || []).forEach((p: any) => {
      if (p.location && p.location.length === 2) {
        markers.push({ position: p.location, title: p.name || '候选点' });
      }
    });
    if (payload.value.anchor_loc) center = payload.value.anchor_loc;
  }
  return { center, markers, polylines };
};

const renderMap = async () => {
  if (!mapRef.value || errorMsg.value) return;
  if (mapInstance && typeof mapInstance.destroy === 'function') {
    mapInstance.destroy();
    mapInstance = null;
  }

  const key = String(import.meta.env.VITE_AMAP_WEB_KEY || '').trim();
  if (!key) {
    mapHint.value = '未配置 VITE_AMAP_WEB_KEY，当前展示为纯文本报告。';
    return;
  }

  try {
    await loadAmap(key);
    const AMap = (window as any).AMap;
    if (!AMap) {
      mapHint.value = '地图 SDK 加载失败。';
      return;
    }

    const { center, markers, polylines } = collectMapElements();
    mapInstance = new AMap.Map(mapRef.value, { zoom: 12, center });
    const objects: any[] = [];

    markers.forEach((m) => {
      const marker = new AMap.Marker({ position: m.position, title: m.title });
      objects.push(marker);
      mapInstance.add(marker);
    });

    polylines.forEach((line) => {
      const polyline = new AMap.Polyline({
        path: line,
        strokeColor: '#2f95ff',
        strokeWeight: 6,
        strokeOpacity: 0.85
      });
      objects.push(polyline);
      mapInstance.add(polyline);
    });

    if (objects.length) mapInstance.setFitView(objects, false, [50, 50, 50, 50]);
    mapHint.value = '';
  } catch (e) {
    mapHint.value = '地图加载失败，已降级为纯文本展示。';
  }
};

watch(
  () => route.query,
  async () => {
    parseQuery();
    await nextTick();
    await renderMap();
  },
  { immediate: true }
);
</script>

<style scoped lang="scss">
.embed-page {
  min-height: 100vh;
  margin: 0;
  padding: 12px;
  background: linear-gradient(180deg, #f6f8fb 0%, #ffffff 55%);
  box-sizing: border-box;
  color: #2b2f36;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}

.panel {
  max-width: 1180px;
  margin: 0 auto;
  background: #fff;
  border: 1px solid #e8edf3;
  border-radius: 14px;
  box-shadow: 0 6px 20px rgba(21, 29, 40, 0.05);
  padding: 14px;
}

.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #edf1f6;
  padding-bottom: 10px;
  margin-bottom: 12px;
  h2 {
    margin: 0;
    font-size: 20px;
  }
  .time-text {
    font-size: 12px;
    color: #758194;
  }
}

.section {
  margin-bottom: 14px;
  h3 {
    margin: 0 0 8px;
    font-size: 15px;
  }
}

.meta-grid, .kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.meta-item, .kpi {
  border: 1px solid #ebeff5;
  border-radius: 10px;
  padding: 10px;
  background: #fafcff;
  span {
    display: block;
    font-size: 12px;
    color: #6f7b8d;
    margin-bottom: 4px;
  }
  strong {
    font-size: 14px;
    color: #1f2d3d;
  }
}

.list-block {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid #edf1f6;
  border-radius: 10px;
  background: #fff;
  ul {
    margin: 0;
    padding-left: 18px;
  }
  li {
    margin-bottom: 6px;
    line-height: 1.5;
    font-size: 13px;
  }
  p {
    margin: 0;
    font-size: 13px;
    line-height: 1.5;
  }
}

.map-box {
  width: 100%;
  height: 320px;
  border: 1px solid #e7edf4;
  border-radius: 10px;
  overflow: hidden;
  background: #f3f6fb;
}

.map-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #8793a6;
}

.error-box {
  border: 1px solid #f5d0d0;
  background: #fff5f5;
  color: #b42323;
  border-radius: 10px;
  padding: 12px;
  font-size: 13px;
}

@media (max-width: 768px) {
  .meta-grid, .kpi-grid {
    grid-template-columns: 1fr;
  }
  .map-box {
    height: 240px;
  }
}
</style>
