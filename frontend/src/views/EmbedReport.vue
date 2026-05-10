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

        <section v-if="reportType === 'ev_charge'" class="section">
          <div class="meta-grid">
            <div class="meta-item"><span>起点</span><strong>{{ payload.origin_name || '-' }}</strong></div>
            <div class="meta-item"><span>终点</span><strong>{{ payload.destination_name || '-' }}</strong></div>
            <div class="meta-item"><span>出行风格</span><strong>{{ payload.style || '均衡' }}</strong></div>
            <div class="meta-item"><span>当前电量</span><strong>{{ payload.current_soc ?? '-' }}%</strong></div>
            <div class="meta-item"><span>预留电量</span><strong>{{ payload.reserve_soc ?? '-' }}%</strong></div>
            <div class="meta-item"><span>生成时间</span><strong>{{ payload.generated_at || '-' }}</strong></div>
          </div>

          <div class="kpi-grid">
            <div class="kpi"><span>总距离</span><strong>{{ payload.distance_km ?? '-' }} km</strong></div>
            <div class="kpi"><span>行驶耗时</span><strong>{{ payload.duration_min ?? '-' }} min</strong></div>
            <div class="kpi"><span>建议补能次数</span><strong>{{ (payload.charge_stops || []).length }}</strong></div>
            <div class="kpi"><span>预计总耗时</span><strong>{{ payload.estimated_total_time_min ?? '-' }} min</strong></div>
            <div class="kpi"><span>补能等待</span><strong>{{ payload.total_wait_min ?? '-' }} min</strong></div>
            <div class="kpi"><span>充电费用</span><strong>{{ payload.estimated_energy_cost ?? '-' }} 元</strong></div>
          </div>

          <div class="list-block">
            <h3>建议充电节点</h3>
            <div v-if="!(payload.charge_stops || []).length" class="empty-text">当前电量可覆盖本次行程，暂不建议中途充电。</div>
            <div v-for="(item, idx) in payload.charge_stops || []" :key="`ev-stop-${idx}`" class="charge-stop">
              <strong>{{ item.name }}</strong>
              <p>
                距起点约 {{ item.distance_from_start_km }} km，
                目标电量 {{ item.target_soc }}%，
                预计等待 {{ item.estimated_wait_min }} min，
                充电 {{ item.estimated_charge_min }} min，
                费用约 {{ item.estimated_cost }} 元。
              </p>
              <p v-if="item.address">地址：{{ item.address }}</p>
              <span>{{ item.reason }}</span>
            </div>
          </div>
        </section>

        <section v-if="reportType === 'ev_simulation'" class="section">
          <div class="meta-grid">
            <div class="meta-item"><span>起点</span><strong>{{ payload.origin_name || '-' }}</strong></div>
            <div class="meta-item"><span>终点</span><strong>{{ payload.destination_name || '-' }}</strong></div>
            <div class="meta-item"><span>出行风格</span><strong>{{ payload.style || '均衡' }}</strong></div>
            <div class="meta-item"><span>事件数量</span><strong>{{ simulationEvents.length }}</strong></div>
          </div>

          <div class="sim-player">
            <div class="sim-status">
              <span>{{ simulationStatus }}</span>
              <strong>{{ currentSimulationTitle }}</strong>
              <p>当前 SOC：{{ simulationSoc }}%</p>
              <div class="soc-track">
                <div class="soc-fill" :style="{ width: `${simulationSoc}%` }"></div>
              </div>
            </div>

            <div class="sim-controls">
              <button @click="toggleSimulation">{{ isSimPlaying ? '暂停' : '播放' }}</button>
              <button @click="resetSimulation">重置</button>
            </div>
          </div>

          <div class="timeline">
            <div
              v-for="(item, idx) in simulationEvents"
              :key="`sim-${idx}`"
              :class="simulationItemClass(idx)"
            >
              <div class="dot"></div>
              <div class="timeline-body">
                <strong>{{ formatSimulationEvent(item) }}</strong>
                <p v-if="item.type === 'drive'">
                  {{ item.from }} → {{ item.to }}，{{ item.distance_km }}km，{{ item.duration_min }}min，
                  SOC {{ item.start_soc }}% → {{ item.end_soc }}%
                </p>
                <p v-else>
                  {{ item.station }}，等待 {{ item.wait_min }}min，充电 {{ item.charge_min }}min，
                  SOC {{ item.start_soc }}% → {{ item.end_soc }}%，费用约 {{ item.estimated_cost }} 元
                </p>
              </div>
            </div>
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
import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const reportType = ref('');
const payload = ref<any>({});
const errorMsg = ref('');
const mapHint = ref('');
const mapRef = ref<HTMLElement | null>(null);
let mapInstance: any = null;
let simTimer: number | null = null;
const isSimPlaying = ref(false);
const activeEventIndex = ref(0);
const simProgress = ref(0);

const pageTitle = computed(() => {
  if (reportType.value === 'congestion') return payload.value.title || '城市拥堵体检报告';
  if (reportType.value === 'route') return payload.value.title || '路线规划报告';
  if (reportType.value === 'nearby') return payload.value.title || '周边搜索报告';
  if (reportType.value === 'ev_charge') return payload.value.title || '电动车充电路径规划报告';
  if (reportType.value === 'ev_simulation') return payload.value.title || '电动车充电路径仿真推演';
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

const simulationEvents = computed(() => payload.value.simulation_events || []);

const currentSimulationEvent = computed(() => {
  return simulationEvents.value[activeEventIndex.value] || null;
});

const simulationStatus = computed(() => {
  const event = currentSimulationEvent.value;
  if (!event) return '仿真完成';
  if (event.type === 'charge') return '正在充电';
  return '行驶中';
});

const currentSimulationTitle = computed(() => {
  const event = currentSimulationEvent.value;
  if (!event) return `${payload.value.destination_name || '终点'} 已到达`;
  if (event.type === 'charge') return event.station || '建议充电站';
  return `${event.from || '-'} → ${event.to || '-'}`;
});

const simulationSoc = computed(() => {
  const event = currentSimulationEvent.value;
  if (!event) return payload.value.reserve_soc || 20;
  const start = Number(event.start_soc || 0);
  const end = Number(event.end_soc || start);
  return Math.round(start + (end - start) * simProgress.value);
});

const stopSimulation = () => {
  if (simTimer !== null) {
    window.clearInterval(simTimer);
    simTimer = null;
  }
  isSimPlaying.value = false;
};

const resetSimulation = () => {
  stopSimulation();
  activeEventIndex.value = 0;
  simProgress.value = 0;
};

const tickSimulation = () => {
  if (!simulationEvents.value.length) {
    stopSimulation();
    return;
  }
  simProgress.value += 0.04;
  if (simProgress.value >= 1) {
    simProgress.value = 0;
    activeEventIndex.value += 1;
    if (activeEventIndex.value >= simulationEvents.value.length) {
      activeEventIndex.value = simulationEvents.value.length - 1;
      simProgress.value = 1;
      stopSimulation();
    }
  }
};

const toggleSimulation = () => {
  if (isSimPlaying.value) {
    stopSimulation();
    return;
  }
  if (!simulationEvents.value.length) return;
  if (activeEventIndex.value >= simulationEvents.value.length - 1 && simProgress.value >= 1) {
    resetSimulation();
  }
  isSimPlaying.value = true;
  simTimer = window.setInterval(tickSimulation, 240);
};

const formatSimulationEvent = (item: any) => {
  if (item.type === 'charge') return `充电停靠：${item.station || '建议充电站'}`;
  return `行驶路段：${item.from || '-'} → ${item.to || '-'}`;
};

const simulationItemClass = (idx: any) => {
  const i = Number(idx);
  return ['timeline-item', i === activeEventIndex.value ? 'active' : '', i < activeEventIndex.value ? 'done' : ''];
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
    resetSimulation();
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

const loadAmapPlugin = (pluginName: string) => {
  const AMap = (window as any).AMap;
  return new Promise<void>((resolve, reject) => {
    if (!AMap || typeof AMap.plugin !== 'function') {
      reject(new Error('plugin unavailable'));
      return;
    }
    AMap.plugin(pluginName, () => resolve());
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
  } else if (reportType.value === 'ev_charge' || reportType.value === 'ev_simulation') {
    if (payload.value.origin_loc) markers.push({ position: payload.value.origin_loc, title: payload.value.origin_name || '起点' });
    if (payload.value.destination_loc) markers.push({ position: payload.value.destination_loc, title: payload.value.destination_name || '终点' });
    if (Array.isArray(payload.value.polyline) && payload.value.polyline.length > 1) {
      polylines.push(payload.value.polyline);
    }
    if (payload.value.origin_loc) center = payload.value.origin_loc;
  }
  return { center, markers, polylines };
};

const shouldDrawRoadRoute = () => {
  return ['route', 'ev_charge', 'ev_simulation'].includes(reportType.value)
    && payload.value.origin_loc
    && payload.value.destination_loc;
};

const extractRoadPath = (result: any) => {
  const points: any[] = [];
  const steps = result?.routes?.[0]?.steps || [];
  steps.forEach((step: any) => {
    (step.path || []).forEach((point: any) => points.push(point));
  });
  return points;
};

const pickRoadPoint = (roadPath: any[], fraction: number) => {
  if (!roadPath.length) return null;
  const idx = Math.max(0, Math.min(roadPath.length - 1, Math.round((roadPath.length - 1) * fraction)));
  return roadPath[idx];
};

const addEvStopMarkersOnRoad = (roadPath: any[], objects: any[]) => {
  const AMap = (window as any).AMap;
  const totalDistance = Number(payload.value.distance_km || 0);
  if (!AMap || !roadPath.length || !totalDistance) return;

  (payload.value.charge_stops || []).forEach((stop: any) => {
    const stopDistance = Number(stop.distance_from_start_km || 0);
    const roadPoint = pickRoadPoint(roadPath, stopDistance / totalDistance);
    if (!roadPoint) return;
    const marker = new AMap.Marker({
      position: roadPoint,
      title: stop.name || '建议充电站'
    });
    objects.push(marker);
    mapInstance.add(marker);
  });
};

const drawRoadRoute = async () => {
  const AMap = (window as any).AMap;
  if (!mapInstance || !AMap || !shouldDrawRoadRoute()) return [];

  try {
    await loadAmapPlugin('AMap.Driving');
    const origin = new AMap.LngLat(payload.value.origin_loc[0], payload.value.origin_loc[1]);
    const destination = new AMap.LngLat(payload.value.destination_loc[0], payload.value.destination_loc[1]);
    const driving = new AMap.Driving({
      map: mapInstance,
      policy: AMap.DrivingPolicy.LEAST_TIME,
      hideMarkers: true
    });

    const roadPath = await new Promise<any[]>((resolve, reject) => {
      driving.search(origin, destination, (status: string, result: any) => {
        if (status === 'complete') resolve(extractRoadPath(result));
        else reject(new Error('route fail'));
      });
    });
    return roadPath;
  } catch (e) {
    return [];
  }
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

    const roadPath = await drawRoadRoute();
    if (roadPath.length) {
      addEvStopMarkersOnRoad(roadPath, objects);
    } else {
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
    }

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

onUnmounted(() => {
  stopSimulation();
});
</script>

<style scoped lang="scss">
.embed-page {
  min-height: 100vh;
  margin: 0;
  padding: 18px;
  background: var(--ai-gradient-soft);
  box-sizing: border-box;
  color: #2b2f36;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}

.panel {
  max-width: 1180px;
  margin: 0 auto;
  background: var(--ai-surface);
  border: 1px solid var(--ai-border);
  border-radius: 24px;
  box-shadow: var(--ai-shadow-md);
  padding: 18px;
  backdrop-filter: blur(22px);
}

.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--ai-border);
  padding-bottom: 14px;
  margin-bottom: 16px;
  h2 {
    margin: 0;
    font-size: 22px;
    color: var(--ai-text);
    font-weight: 900;
  }
  .time-text {
    font-size: 12px;
    color: #758194;
  }
}

.section {
  margin-bottom: 16px;
  h3 {
    margin: 0 0 8px;
    font-size: 15px;
    color: var(--ai-text);
    font-weight: 800;
  }
}

.meta-grid, .kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.meta-item, .kpi {
  border: 1px solid var(--ai-border);
  border-radius: 14px;
  padding: 12px;
  background: rgba(255,255,255,0.78);
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
  padding: 12px;
  border: 1px solid var(--ai-border);
  border-radius: 14px;
  background: rgba(255,255,255,0.86);
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

.charge-stop {
  padding: 10px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  &:last-child {
    border-bottom: none;
  }
  strong {
    display: block;
    font-size: 14px;
    color: #1f2d3d;
    margin-bottom: 4px;
  }
  p {
    margin: 0 0 4px;
  }
  span {
    display: block;
    font-size: 12px;
    color: #6f7b8d;
  }
}

.empty-text {
  font-size: 13px;
  color: #6f7b8d;
}

.sim-player {
  margin-top: 12px;
  padding: 14px;
  border: 1px solid var(--ai-border);
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.94), rgba(255,255,255,0.9));
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.sim-status {
  flex: 1;
  span {
    display: inline-flex;
    margin-bottom: 6px;
    padding: 3px 9px;
    border-radius: 999px;
    background: #eaf4ff;
    color: #1f5b90;
    font-size: 12px;
    font-weight: 700;
  }
  strong {
    display: block;
    font-size: 18px;
    color: var(--ai-text);
    margin-bottom: 4px;
  }
  p {
    margin: 0 0 8px;
    font-size: 13px;
    color: #526071;
  }
}

.soc-track {
  height: 10px;
  border-radius: 999px;
  background: #dbe6f3;
  overflow: hidden;
}

.soc-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #1fb981, #44d7a8);
  transition: width 0.22s ease;
}

.sim-controls {
  display: flex;
  gap: 8px;
  button {
    border: none;
    border-radius: 999px;
    padding: 8px 14px;
    cursor: pointer;
    background: var(--ai-gradient);
    color: #fff;
    font-weight: 800;
  }
  button + button {
    background: #eef2f7;
    color: #334155;
  }
}

.timeline {
  margin-top: 12px;
  border: 1px solid var(--ai-border);
  border-radius: 18px;
  background: rgba(255,255,255,0.86);
  padding: 12px;
}

.timeline-item {
  display: flex;
  gap: 10px;
  padding: 10px 0;
  opacity: 0.55;
  .dot {
    width: 10px;
    height: 10px;
    margin-top: 6px;
    border-radius: 50%;
    background: #cbd5e1;
    flex: 0 0 auto;
  }
  &.active, &.done {
    opacity: 1;
  }
  &.active .dot {
    background: #2f95ff;
    box-shadow: 0 0 0 5px rgba(47,149,255,0.12);
  }
  &.done .dot {
    background: #1fb981;
  }
}

.timeline-body {
  strong {
    display: block;
    font-size: 14px;
    color: #1f2d3d;
    margin-bottom: 3px;
  }
  p {
    margin: 0;
    font-size: 13px;
    color: #526071;
    line-height: 1.55;
  }
}

.map-box {
  width: 100%;
  height: 360px;
  border: 1px solid var(--ai-border);
  border-radius: 18px;
  overflow: hidden;
  background: #f3f6fb;
  box-shadow: var(--ai-shadow-sm);
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
