<template>
  <div class="glass-provider">
    <div class="bg-bubble bubble-1"></div>
    <div class="bg-bubble bubble-2"></div>

    <div class="app-container">
      <!-- 侧边栏 -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <el-button class="new-chat-btn" type="primary" @click="createNewChat">
            <el-icon><Plus /></el-icon> 开启新对话
          </el-button>
        </div>
        
        <div class="session-list custom-scrollbar">
          <transition-group name="list">
            <div v-for="s in sessions" :key="s.id" :class="['session-card', currentSessionId === s.id ? 'active' : '']" @click="switchSession(s.id)">
              <div class="session-icon"><el-icon><ChatDotSquare /></el-icon></div>
              <div class="session-info">
                <span class="title">{{ s.title }}</span>
                <span class="time">{{ formatTime(s.updated_at) }}</span>
              </div>
              <el-icon class="delete-btn" @click.stop="deleteSession(s.id)"><Delete /></el-icon>
            </div>
          </transition-group>
        </div>

        <!-- 侧边栏底部：跳转个人信息 -->
        <div class="sidebar-footer" @click="$router.push('/profile')">
          <div class="user-profile">
            <img :src="fullAvatarUrl" class="mini-avatar" />
            <div class="user-texts">
              <span class="name">{{ currentUser.username || '加载中...' }}</span>
              <span class="status">在线 · 点击设置</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 右侧主对话区 -->
      <main class="chat-main">
        <header class="main-header">
          <div class="header-info">
            <span class="session-label">当前会话</span>
            <h3 class="current-title">{{ currentSessionTitle }}</h3>
          </div>
          <el-button circle :icon="Refresh" @click="fetchHistory(currentSessionId)" />
        </header>

        <div class="message-wall custom-scrollbar" ref="messageBox">
          <!-- 欢迎页 -->
          <div v-if="chatHistory.length === 0" class="welcome-section">
            <div class="welcome-card">
              <div class="hero-icon">🚗</div>
              <h1>您好！我是交通法智能助手</h1>
              <p>我已经深度学习了《中华人民共和国道路交通安全法》，您可以向我提问相关的法律条文。</p>
              <div class="quick-tips">
                <div class="tip-item" @click="quickStart('饮酒驾驶如何处罚？')">🍺 酒驾处罚</div>
                <div class="tip-item" @click="quickStart('发生交通事故如何处理？')">🚑 事故处理</div>
                <div class="tip-item" @click="quickStart('机动车登记材料？')">📝 车辆登记</div>
              </div>
            </div>
          </div>

          <!-- 对话列表 -->
          <transition-group name="msg">
            <div v-for="(msg, index) in chatHistory" :key="index" :class="['msg-row', msg.role === 'user' ? 'is-user' : 'is-ai']">
              <div class="msg-bubble">
                <div class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
                
                <div v-if="msg.role === 'ai' && msg.sources?.length" class="source-container">
                  <el-divider border-style="dashed" />
                  <el-popover placement="top-start" title="法律条文依据" :width="500" trigger="click">
                    <template #reference>
                      <span class="source-trigger"><el-icon><Document /></el-icon> 查看法律原文</span>
                    </template>
                    <!-- 关键修复：增加高度限制和滚动条 -->
                    <div class="source-popover-content">
                      <div v-for="(s, i) in msg.sources" :key="i" class="source-text-item">
                        <b>依据 {{ i + 1 }}:</b> {{ s }}
                      </div>
                    </div>
                  </el-popover>
                </div>
              </div>
            </div>
          </transition-group>
          
          <div v-if="loading" class="msg-row is-ai">
            <div class="msg-bubble loading-bubble"><div class="typing-loader"></div><span>正在查阅法律法规...</span></div>
          </div>
        </div>

        <footer class="input-container">
          <div class="input-wrapper">
            <el-input v-model="inputQuery" placeholder="描述您的问题，按回车发送..." type="textarea" :autosize="{ minRows: 1, maxRows: 5 }" resize="none" @keyup.enter.prevent="handleSend" />
            <el-button type="primary" circle @click="handleSend" :loading="loading" :icon="Top" />
          </div>
          <div class="footer-hint">AI 生成内容仅供参考，请以官方纸质法律条文为准</div>
        </footer>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue';
import { Plus, ChatDotSquare, Delete, Refresh, Document, Top } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import request from '../api/request';
import MarkdownIt from 'markdown-it';

interface SessionItem { id: string; title: string; updated_at?: string; }
interface Message { role: 'user' | 'ai'; content: string; sources?: string[]; }

const sessions = ref<SessionItem[]>([]);
const currentSessionId = ref('');
const chatHistory = ref<Message[]>([]);
const inputQuery = ref('');
const loading = ref(false);
const messageBox = ref<HTMLElement | null>(null);
const currentUser = ref({ username: '', avatar: '' });

const md = new MarkdownIt({ html: true });

const fullAvatarUrl = computed(() => {
  return currentUser.value.avatar 
    ? `http://localhost:8000${currentUser.value.avatar}` 
    : 'https://api.dicebear.com/7.x/avataaars/svg?seed=Felix';
});

const currentSessionTitle = computed(() => sessions.value.find(i => i.id === currentSessionId.value)?.title || '新对话');

onMounted(async () => {
   loading.value = true;
  
  // 使用并发请求且独立捕获错误，防止一个 404 导致全盘崩溃
  try {
    const [userRes, sessionRes] = await Promise.all([
      request.get('/v1/chat/me').catch(_e => ({ data: null })),
      request.get('/v1/chat/sessions').catch(_e => ({ data: [] }))
    ]);

    if (userRes.data) currentUser.value = userRes.data;
    if (sessionRes.data) sessions.value = sessionRes.data;

    // 处理初始化会话
    const firstId = sessions.value[0]?.id;
    if (firstId) {
      switchSession(firstId);
    } else {
      createNewChat(); // 此时 chatHistory 为空，显示欢迎界面
    }
  } catch (error) {
    console.error("初始化失败", error);
  } finally {
    loading.value = false;
  }
  await fetchUser();
  await fetchSessions();
  const firstId = sessions.value[0]?.id;
  if (firstId) switchSession(firstId); else createNewChat();
});

const fetchUser = async () => {
  const res = await request.get('/v1/chat/me');
  currentUser.value = res.data;
};

const fetchSessions = async () => {
  const res = await request.get('/v1/chat/sessions');
  sessions.value = res.data;
};

const fetchHistory = async (id: string) => {
  if (!id) return;
  const res = await request.get(`/v1/chat/history/${id}`);
  chatHistory.value = res.data.map((m: any) => ({
    role: m.role, content: m.content, sources: typeof m.sources === 'string' ? JSON.parse(m.sources) : m.sources
  }));
  await scrollToBottom();
};

const switchSession = (id: string) => { currentSessionId.value = id; fetchHistory(id); };

const createNewChat = () => {
  currentSessionId.value = `session_${Math.random().toString(36).substr(2, 9)}`;
  chatHistory.value = [];
};

const handleSend = async () => {
  if (!inputQuery.value.trim() || loading.value) return;
  const question = inputQuery.value.trim();
  chatHistory.value.push({ role: 'user', content: question });
  inputQuery.value = '';
  loading.value = true;
  await scrollToBottom();
  try {
    const res = await request.post('/v1/chat/ask', { question, session_id: currentSessionId.value });
    if (res.data.status === 'success') {
      chatHistory.value.push({ role: 'ai', content: res.data.answer, sources: res.data.sources });
      await fetchSessions();
    }
  } catch (error) { ElMessage.error('AI 响应失败'); } finally { loading.value = false; await scrollToBottom(); }
};

const quickStart = (t: string) => { inputQuery.value = t; handleSend(); };
const formatTime = (t?: string) => t ? new Date(t).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '刚刚';
const renderMarkdown = (t: string) => md.render(t);
const scrollToBottom = async () => {
  await nextTick();
  if (messageBox.value) messageBox.value.scrollTo({ top: messageBox.value.scrollHeight, behavior: 'smooth' });
};
const deleteSession = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定删除吗？');
    sessions.value = sessions.value.filter(s => s.id !== id);
    if (currentSessionId.value === id) createNewChat();
  } catch (e) {}
};
</script>

<style scoped lang="scss">
/* 此处包含之前所有的 Glassmorphism 样式，并增加法律原文滚动修复 */
.glass-provider { height: 100vh; width: 100vw; background: #eef2f7; display: flex; justify-content: center; align-items: center; position: relative; overflow: hidden; }
.bg-bubble { position: absolute; border-radius: 50%; filter: blur(80px); z-index: 0; }
.bubble-1 { width: 400px; height: 400px; background: rgba(64, 158, 255, 0.2); top: -100px; left: -100px; }
.bubble-2 { width: 500px; height: 500px; background: rgba(103, 194, 58, 0.15); bottom: -150px; right: -150px; }
.app-container { width: 96%; height: 94%; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(25px); border: 1px solid rgba(255, 255, 255, 0.6); border-radius: 28px; display: flex; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.1); z-index: 1; overflow: hidden; }

.sidebar { width: 280px; background: rgba(255, 255, 255, 0.3); border-right: 1px solid rgba(0, 0, 0, 0.05); display: flex; flex-direction: column; padding: 24px 16px; 
  .new-chat-btn { width: 100%; height: 48px; border-radius: 14px; margin-bottom: 24px; font-weight: 600; }
  .sidebar-footer { margin-top: auto; padding: 15px; border-radius: 15px; background: rgba(255,255,255,0.5); cursor: pointer; transition: 0.3s; &:hover { background: #fff; }
    .user-profile { display: flex; align-items: center; gap: 12px; .mini-avatar { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; }
      .user-texts { display: flex; flex-direction: column; .name { font-size: 13px; font-weight: bold; } .status { font-size: 10px; color: #67C23A; } }
    }
  }
}

.session-list { flex: 1; overflow-y: auto; .session-card { padding: 12px; margin-bottom: 8px; border-radius: 12px; display: flex; align-items: center; gap: 10px; cursor: pointer; position: relative; border: 1px solid transparent; transition: 0.2s; &:hover { background: rgba(255,255,255,0.6); .delete-btn { opacity: 1; } } &.active { background: #fff; border-color: #409eff; } .title { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; } .time { font-size: 10px; color: #999; } .delete-btn { opacity: 0; color: #f56c6c; } } }

.chat-main { flex: 1; display: flex; flex-direction: column; position: relative; }
.main-header { padding: 15px 30px; border-bottom: 1px solid rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; .current-title { margin: 0; font-size: 18px; } }
.message-wall { flex: 1; padding: 30px 15% 120px 15%; overflow-y: auto; scroll-behavior: smooth; }

.welcome-section { display: flex; justify-content: center; align-items: center; height: 100%; text-align: center; .hero-icon { font-size: 60px; margin-bottom: 20px; } .quick-tips { display: flex; gap: 10px; justify-content: center; margin-top: 20px; .tip-item { padding: 8px 15px; background: #fff; border-radius: 10px; font-size: 12px; cursor: pointer; transition: 0.3s; &:hover { color: #409eff; transform: translateY(-2px); } } } }

.msg-row { display: flex; margin-bottom: 25px; &.is-user { justify-content: flex-end; .msg-bubble { background: #409eff; color: #fff; border-radius: 18px 18px 4px 18px; } } &.is-ai { justify-content: flex-start; .msg-bubble { background: #fff; color: #333; border-radius: 18px 18px 18px 4px; border: 1px solid #eee; } } .msg-bubble { max-width: 85%; padding: 15px 20px; line-height: 1.6; } }

/* 修复法律原文弹出层滚动 */
.source-popover-content {
  max-height: 350px; overflow-y: auto; padding-right: 5px;
  .source-text-item { margin-bottom: 10px; padding: 10px; background: #f8f9fa; border-radius: 8px; font-size: 13px; line-height: 1.5; border: 1px solid #eee; b { color: #409eff; display: block; margin-bottom: 5px; } }
  &::-webkit-scrollbar { width: 4px; } &::-webkit-scrollbar-thumb { background: #ddd; border-radius: 2px; }
}
.source-trigger { font-size: 12px; color: #409eff; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; margin-top: 10px; }

.input-container { position: absolute; bottom: 20px; left: 15%; right: 15%; .input-wrapper { background: #fff; border-radius: 18px; padding: 10px; display: flex; align-items: flex-end; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid #eee; &:focus-within { border-color: #409eff; } :deep(.el-textarea__inner) { border: none; box-shadow: none; font-size: 15px; } } .footer-hint { text-align: center; font-size: 11px; color: #999; margin-top: 10px; } }

.custom-scrollbar::-webkit-scrollbar { width: 5px; } .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 10px; }
.typing-loader { width: 10px; height: 10px; background: #409eff; border-radius: 50%; animation: pulse 1s infinite; }
@keyframes pulse { 0% { transform: scale(0.8); opacity: 0.5; } 50% { transform: scale(1.2); opacity: 1; } 100% { transform: scale(0.8); opacity: 0.5; } }
</style>