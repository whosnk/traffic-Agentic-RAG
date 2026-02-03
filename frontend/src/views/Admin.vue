<template>
  <div class="admin-page">
    <div class="bg-glow"></div>
    <div class="glass-card custom-scrollbar">
      <!-- 1. 标题与上传区域 -->
      <header class="admin-header">
        <div class="title-section">
          <el-icon :size="28" color="#409eff"><Collection /></el-icon>
          <h2>交通法知识库管理</h2>
        </div>
        <el-upload 
          action="/api/v1/chat/upload" 
          :headers="headers" 
          :on-success="onUploadSuccess" 
          :show-file-list="false"
        >
          <el-button type="primary" :icon="Plus" round>上传 PDF 法律法规</el-button>
        </el-upload>
      </header>

      <!-- 2. 知识库列表表格 -->
      <div class="table-wrapper">
        <el-table :data="docs" style="width: 100%" class="modern-table">
          <el-table-column prop="filename" label="文件名" min-width="250" />
          <el-table-column prop="chunk_count" label="切片数量" width="120" align="center" />
          <el-table-column prop="upload_time" label="上传时间" width="200" align="center">
            <template #default="scope">
              {{ formatTime(scope.row.upload_time) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center">
            <template #default="scope">
              <el-button type="danger" link @click="handleDelete(scope.row)">
                <el-icon><Delete /></el-icon> 清空索引
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 3. 数据分析看板区域 -->
      <div class="analytics-dashboard">
        <el-divider content-position="left">
          <el-icon><PieChart /></el-icon> 用户提问热点分析 (K-Means)
        </el-divider>

        <el-row :gutter="20">
          <!-- 左侧：ECharts 环形图 -->
          <el-col :span="10">
            <div class="inner-card chart-box">
              <div ref="chartRef" style="height: 350px; width: 100%;"></div>
            </div>
          </el-col>

          <!-- 右侧：AI 热点话题列表 -->
          <el-col :span="14">
            <div class="inner-card topic-list">
              <h3>🔥 智能识别热点话题</h3>
              <el-scrollbar height="300px">
                <div v-if="hotTopics.length === 0" class="no-data">暂无分析数据，请点击下方按钮运行</div>
                <div v-for="item in hotTopics" :key="item.id" class="topic-item">
                  <div class="topic-header">
                    <span class="topic-title">{{ item.topic_name }}</span>
                    <el-tag size="small" type="danger" effect="dark">{{ item.hit_count }} 次咨询</el-tag>
                  </div>
                  <div class="topic-keywords">
                    <el-tag v-for="k in item.keywords" :key="k" size="small" effect="plain" class="k-tag"># {{ k }}</el-tag>
                  </div>
                  <div class="topic-preview">
                    <p v-for="(q, idx) in item.representative_queries" :key="idx">“ {{ q }} ”</p>
                  </div>
                </div>
              </el-scrollbar>
            </div>
          </el-col>
        </el-row>

        <div class="action-bar">
          <el-button type="primary" :loading="analyzing" @click="startAnalysis" round>
            <el-icon v-if="!analyzing"><Refresh /></el-icon> 重新运行 AI 聚类分析
          </el-button>
        </div>
      </div>

      <!-- 4. 底部状态栏 -->
      <footer class="admin-footer">
        <el-statistic title="系统总切片数" :value="totalChunks" />
        <el-button @click="$router.back()" link :icon="ArrowLeft">返回聊天</el-button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue';
import { Plus, Collection, Delete, ArrowLeft, PieChart, Refresh } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import request from '../api/request';
import * as echarts from 'echarts';

// --- 类型接口定义 ---
interface DocItem {
  id: number;
  filename: string;
  chunk_count: number;
  upload_time: string;
}

interface HotTopic {
  id: number;
  topic_name: string;
  keywords: string[];
  hit_count: number;
  representative_queries: string[];
}

// --- 响应式变量 ---
const docs = ref<DocItem[]>([]);
const hotTopics = ref<HotTopic[]>([]);
const chartRef = ref<HTMLElement | null>(null);
const analyzing = ref(false);
const headers = { Authorization: `Bearer ${localStorage.getItem('access_token')}` };

// --- ECharts 初始化 ---
const initChart = (data: { topic: string; count: number }[]) => {
  if (!chartRef.value || !data.length) return;
  
  const myChart = echarts.init(chartRef.value);
  const option = {
    title: { text: '咨询热点分布', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: data.map(item => ({ value: item.count, name: item.topic }))
      }
    ]
  };
  myChart.setOption(option);
  window.addEventListener('resize', () => myChart.resize());
};

// --- API 调用 ---
const fetchHotTopics = async () => {
  try {
    const res = await request.get('/v1/chat/analytics');
    hotTopics.value = res.data;
    if (hotTopics.value.length > 0) {
      await nextTick();
      initChart(hotTopics.value.map(i => ({ topic: i.topic_name, count: i.hit_count })));
    }
  } catch (e) {
    console.error("加载分析数据失败");
  }
};

const fetchDocs = async () => {
  try {
    const res = await request.get('/v1/chat/knowledge_list');
    docs.value = res.data;
    await fetchHotTopics();
  } catch (e) {
    ElMessage.error('获取知识库列表失败');
  }
};

const startAnalysis = async () => {
  analyzing.value = true;
  try {
    await request.post('/v1/chat/perform_analysis');
    ElMessage.success('分析引擎运行成功');
    await fetchHotTopics();
  } catch (e) {
    ElMessage.error('分析失败，请确保数据库有足够对话数据');
  } finally {
    analyzing.value = false;
  }
};

const onUploadSuccess = () => {
  ElMessage.success('文件上传并切片成功');
  fetchDocs();
};

const handleDelete = async (row: DocItem) => {
  try {
    await ElMessageBox.confirm(`确定要清空 [${row.filename}] 的索引吗？`, '警示', { type: 'warning' });
    await request.delete(`/v1/chat/knowledge/${row.id}`);
    ElMessage.success('删除成功');
    fetchDocs();
  } catch (e) {}
};

// --- 辅助计算 ---
const totalChunks = computed(() => docs.value.reduce((acc, cur) => acc + cur.chunk_count, 0));
const formatTime = (t: string) => new Date(t).toLocaleString();

onMounted(fetchDocs);
</script>

<style scoped lang="scss">
.admin-page {
  height: 100vh; width: 100vw; display: flex; justify-content: center; align-items: center;
  background: #f0f2f5; position: relative; overflow: hidden;
}
.bg-glow {
  position: absolute; width: 600px; height: 600px; background: rgba(64, 158, 255, 0.1);
  filter: blur(100px); top: -200px; left: -200px;
}
.glass-card {
  width: 1100px; height: 92%; background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px); border-radius: 24px; border: 1px solid rgba(255,255,255,0.5);
  display: flex; flex-direction: column; padding: 30px; box-shadow: 0 20px 50px rgba(0,0,0,0.05);
  overflow-y: auto;
}
.admin-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
  .title-section { display: flex; align-items: center; gap: 15px; h2 { margin: 0; font-size: 22px; } }
}
.table-wrapper { margin-bottom: 30px; }
.analytics-dashboard {
  .inner-card {
    background: rgba(255,255,255,0.4); border-radius: 16px; padding: 20px; border: 1px solid rgba(0,0,0,0.03);
  }
  .no-data { text-align: center; color: #999; padding: 40px; }
  .action-bar { text-align: center; margin-top: 20px; margin-bottom: 20px; }
}
.topic-item {
  background: #fff; padding: 15px; border-radius: 12px; margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
  .topic-header { display: flex; justify-content: space-between; align-items: center;
    .topic-title { font-weight: bold; color: #333; }
  }
  .topic-keywords { margin: 8px 0; display: flex; gap: 5px; }
  .topic-preview { font-size: 12px; color: #888; font-style: italic; p { margin: 4px 0; } }
}
.admin-footer {
  margin-top: auto; padding-top: 20px; border-top: 1px solid rgba(0,0,0,0.05);
  display: flex; justify-content: space-between; align-items: center;
}
.custom-scrollbar::-webkit-scrollbar { width: 5px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 10px; }
</style>