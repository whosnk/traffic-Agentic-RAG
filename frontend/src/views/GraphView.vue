<template>
  <div class="graph-container">
    <div class="glass-card">
      <div class="header">
        <div class="title-group">
          <el-icon class="mesh-icon"><Share /></el-icon>
          <h2>法律逻辑知识图谱</h2>
        </div>
        <el-button @click="$router.back()" circle :icon="ArrowLeft" />
      </div>
      <div ref="chartRef" class="chart-area"></div>
      <div class="legend-custom">
        <div class="l-item"><span class="dot behavior"></span> 违法行为</div>
        <div class="l-item"><span class="dot penalty"></span> 处罚措施</div>
        <div class="l-item"><span class="dot money"></span> 罚款金额</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ArrowLeft, Share } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import request from '../api/request';

const chartRef = ref<HTMLElement | null>(null);

const categoryColors: any = {
  'VIOLATION': '#5470c6',
  'PENALTY': '#91cc75',
  'BASIS': '#fac858',
  'MONEY': '#ee6666',
  'LIMIT': '#73c0de',
  'VEHICLE': '#3ba272'
};

onMounted(async () => {
  const res = await request.get('/v1/chat/knowledge_graph');
  const data = res.data;

  if (!chartRef.value) return;
  const myChart = echarts.init(chartRef.value);

  const option = {
    tooltip: { trigger: 'item', formatter: '{b}' },
    series: [{
      type: 'graph',
      layout: 'force',
      animation: true,
      draggable: true,
      data: data.nodes.map((n: any) => ({
        name: n.name,
        itemStyle: { color: categoryColors[n.category] || '#ccc' },
        symbolSize: n.category === 'VIOLATION' ? 60 : 35,
        label: { show: true, fontSize: 12 }
      })),
      links: data.links.map((l: any) => ({
        source: l.source,
        target: l.target,
        label: { show: true, formatter: l.value, fontSize: 10 },
        lineStyle: { curveness: 0.2, width: 2, opacity: 0.7 }
      })),
      force: {
        repulsion: 1500,
        edgeLength: 180,
        gravity: 0.1
      },
      emphasis: { focus: 'adjacency', lineStyle: { width: 4 } },
      roam: true
    }]
  };

  myChart.setOption(option);
});
</script>

<style scoped lang="scss">
.graph-container {
  height: 100vh; width: 100vw; display: flex; justify-content: center; align-items: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}
.glass-card {
  width: 94%; height: 92%; background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px); border-radius: 30px; padding: 30px;
  display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0,0,0,0.1);
}
.header {
  display: flex; justify-content: space-between; align-items: center;
  .title-group { display: flex; align-items: center; gap: 15px; h2 { margin: 0; font-size: 24px; color: #333; } }
}
.chart-area { flex: 1; margin-top: 20px; }
.legend-custom {
  display: flex; gap: 20px; justify-content: center; padding-top: 10px;
  .l-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #666; }
  .dot { width: 12px; height: 12px; border-radius: 50%; }
  .behavior { background: #5470c6; }
  .penalty { background: #91cc75; }
  .money { background: #ee6666; }
}
</style>