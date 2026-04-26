<template>
  <div class="glass-provider">
    <div class="bg-glow"></div>

    <div class="app-container">
      <!-- 顶部导航 -->
      <header class="page-header">
        <el-button :icon="ArrowLeft" circle @click="$router.back()" />
        <div class="header-title">
          <h2>AI 引擎配置中心</h2>
          <p>Bring Your Own Key (BYOK)</p>
        </div>
        <el-button type="primary" :loading="saving" round @click="saveSettings">保存</el-button>
      </header>

      <div class="settings-content custom-scrollbar">
        <div class="tip-banner">
          <el-icon><InfoFilled /></el-icon>
          <span>提示：您可以为不同场景选择专属的 AI 模型。API Key 若留空，则默认消耗系统公共额度。</span>
        </div>

        <!-- 1. 文本大模型设置 -->
        <section class="config-section">
          <div class="section-title">
            <div class="icon-box llm-icon"><el-icon><ChatDotRound /></el-icon></div>
            <h3>文本对话大模型 (LLM)</h3>
          </div>
          <div class="glass-card">
            <div class="form-group">
              <label>首选模型提供商</label>
              <div class="model-grid">
                <div 
                  v-for="m in llmModels" :key="m.id" 
                  :class="['model-card', form.llm_model === m.id ? 'active' : '']"
                  @click="form.llm_model = m.id"
                >
                  <img :src="m.logo" class="m-logo" />
                  <span class="m-name">{{ m.name }}</span>
                </div>
              </div>
            </div>
            <div class="form-group">
              <label>个人 API Key (可选)</label>
              <el-input 
                v-model="form.llm_key" 
                type="password" 
                show-password 
                placeholder="sk-... (留空则使用系统默认)" 
                class="modern-input"
              />
            </div>
          </div>
        </section>

        <!-- 2. 向量大模型设置 -->
        <section class="config-section">
          <div class="section-title">
            <div class="icon-box embed-icon"><el-icon><DataLine /></el-icon></div>
            <h3>向量检索模型 (Embedding)</h3>
          </div>
          <div class="glass-card">
            <div class="form-group">
              <label>向量化模型选择</label>
              <el-select v-model="form.embed_model" class="modern-select" style="width: 100%">
                <el-option label="阿里通义 Text-Embedding-V4" value="text-embedding-v4" />
                <el-option label="OpenAI text-embedding-3-small" value="text-embedding-3-small" />
              </el-select>
            </div>
            <div class="form-group">
              <label>个人 API Key (可选)</label>
              <el-input v-model="form.embed_key" type="password" show-password placeholder="留空则使用系统默认" class="modern-input"/>
            </div>
          </div>
        </section>

        <!-- 3. 多模态视觉大模型设置 -->
        <section class="config-section">
          <div class="section-title">
            <div class="icon-box vision-icon"><el-icon><Picture /></el-icon></div>
            <h3>多模态视觉模型 (Vision)</h3>
            <el-tag size="small" type="warning" round>即将开放</el-tag>
          </div>
          <div class="glass-card disabled-card">
            <div class="form-group">
              <label>图像分析模型</label>
              <el-select v-model="form.vision_model" class="modern-select" style="width: 100%">
                <el-option label="阿里 Qwen-VL-Max" value="qwen-vl-max" />
                <el-option label="OpenAI GPT-4o" value="gpt-4o" />
              </el-select>
            </div>
            <div class="form-group">
              <label>个人 API Key (可选)</label>
              <el-input v-model="form.vision_key" type="password" show-password placeholder="留空则使用系统默认" class="modern-input"/>
            </div>
          </div>
        </section>

        <div class="bottom-spacer"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ArrowLeft, InfoFilled, ChatDotRound, DataLine, Picture } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import request from '../api/request';

const saving = ref(false);

// 替换成了网络上稳定可用的Logo图片地址
const llmModels =[
  { 
    id: 'deepseek-chat', 
    name: 'DeepSeek V3', 
    logo: 'https://uxwing.com/wp-content/themes/uxwing/download/brands-and-social-media/deepseek-logo-icon.png' 
  },
  { 
    id: 'qwen-max', 
    name: '通义千问 Max', 
    logo: 'https://upload.wikimedia.org/wikipedia/commons/6/69/Qwen_logo.svg' 
  },
  { 
    id: 'gpt-4o', 
    name: 'GPT-4o', 
    logo: 'https://upload.wikimedia.org/wikipedia/commons/0/04/ChatGPT_logo.svg' 
  },
];

const form = ref({
  llm_model: 'deepseek-chat',
  llm_key: '',
  embed_model: 'text-embedding-v4',
  embed_key: '',
  vision_model: 'qwen-vl-max',
  vision_key: ''
});

onMounted(async () => {
  try {
    const res = await request.get('/v1/chat/ai_settings');
    form.value = res.data;
  } catch (e) {
    ElMessage.error('加载配置失败');
  }
});

const saveSettings = async () => {
  saving.value = true;
  try {
    await request.post('/v1/chat/ai_settings', form.value);
    ElMessage.success('配置已保存，将在下次对话中生效');
  } catch (e) {
    ElMessage.error('保存失败');
  } finally {
    saving.value = false;
  }
};
</script>

<style scoped lang="scss">
.glass-provider {
  height: 100vh; width: 100vw; background: var(--ai-gradient-soft); display: flex; justify-content: center; align-items: center; position: relative; overflow: hidden;
}

.bg-glow { position: absolute; width: 600px; height: 600px; background: radial-gradient(circle, rgba(37, 99, 235, 0.16) 0%, transparent 70%); filter: blur(80px); top: -100px; right: -100px; z-index: 0; }

.app-container {
  width: 95%; max-width: 860px; height: 95%; background: var(--ai-surface); backdrop-filter: blur(24px);
  border-radius: 28px; border: 1px solid var(--ai-border); display: flex; flex-direction: column; box-shadow: var(--ai-shadow-md); z-index: 1; overflow: hidden;
  
  @media (max-width: 768px) { width: 100%; height: 100%; border-radius: 0; }
}

.page-header {
  padding: 20px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--ai-border);
  .header-title { text-align: center; h2 { margin: 0; font-size: 19px; color: var(--ai-text); font-weight: 900; } p { margin: 2px 0 0; font-size: 11px; color: var(--ai-text-soft); } }
}

.settings-content {
  flex: 1; padding: 24px; overflow-y: auto;
  @media (max-width: 768px) { padding: 16px; }
}

.tip-banner {
  display: flex; align-items: flex-start; gap: 8px; padding: 13px 16px; background: rgba(37,99,235,0.08); color: var(--ai-primary); border: 1px solid var(--ai-border-strong); border-radius: 16px; font-size: 13px; line-height: 1.5; margin-bottom: 30px;
}

.config-section {
  margin-bottom: 35px;
  .section-title { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; 
    h3 { margin: 0; font-size: 16px; color: var(--ai-text); font-weight: 800; flex: 1;}
    .icon-box { width: 32px; height: 32px; border-radius: 10px; display: flex; justify-content: center; align-items: center; color: white; }
    .llm-icon { background: var(--ai-gradient); }
    .embed-icon { background: linear-gradient(135deg, #16a34a, #22c55e); }
    .vision-icon { background: linear-gradient(135deg, #f59e0b, #f97316); }
  }
}

.glass-card {
  background: rgba(255, 255, 255, 0.78); border: 1px solid var(--ai-border); border-radius: 20px; padding: 22px; box-shadow: var(--ai-shadow-sm);
  &.disabled-card { opacity: 0.6; pointer-events: none; filter: grayscale(100%); }
}

.form-group {
  margin-bottom: 20px; &:last-child { margin-bottom: 0; }
  label { display: block; font-size: 13px; font-weight: 800; color: var(--ai-text); margin-bottom: 10px; }
}

/* 移动端适配的模型选择网格 */
.model-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
  @media (max-width: 600px) { grid-template-columns: 1fr; } /* 手机端单列排布 */
  
  .model-card {
    background: #fff; border: 1px solid var(--ai-border); border-radius: 16px; padding: 16px 10px; text-align: center; cursor: pointer; transition: 0.3s;
    display: flex; flex-direction: column; align-items: center; gap: 8px;
    &:hover { border-color: var(--ai-border-strong); transform: translateY(-2px); box-shadow: var(--ai-shadow-sm); }
    &.active { border-color: var(--ai-primary); background: rgba(37,99,235,0.06); box-shadow: 0 10px 24px rgba(37,99,235,0.12); .m-name { color: var(--ai-primary); font-weight: bold; } }
    .m-logo { width: 36px; height: 36px; object-fit: contain; }
    .m-name { font-size: 13px; color: #666; transition: 0.3s; }
  }
}

:deep(.modern-input .el-input__wrapper) { background: #fff; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); padding: 6px 15px; }
:deep(.modern-select .el-input__wrapper) { background: #fff; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.02); }

.bottom-spacer { height: 40px; }
.custom-scrollbar::-webkit-scrollbar { width: 5px; } .custom-scrollbar::-webkit-scrollbar-thumb { background: #ddd; border-radius: 10px; }
</style>