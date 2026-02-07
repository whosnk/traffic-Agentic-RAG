<template>
  <div class="glass-provider">
    <div class="bg-bubble bubble-1"></div>
    <div class="bg-bubble bubble-2"></div>

    <div class="app-container">
      <!-- 1. 侧边栏：仅在电脑端(Desktop)显示 -->
      <aside class="sidebar desktop-only">
        <div class="sidebar-content">
          <div class="sidebar-header">
            <el-button class="new-chat-btn" type="primary" @click="createNewChat" :icon="Plus">开启新对话</el-button>
          </div>
          <div class="session-list custom-scrollbar">
            <div v-for="s in sessions" :key="s.id" :class="['session-card', currentSessionId === s.id ? 'active' : '']" @click="switchSession(s.id)">
              <el-icon class="session-icon"><ChatDotSquare /></el-icon>
              <div class="session-info">
                <span class="title">{{ s.title }}</span>
                <span class="time">{{ formatTime(s.updated_at) }}</span>
              </div>
              <el-icon class="delete-btn" @click.stop="deleteSession(s.id)"><Delete /></el-icon>
            </div>
          </div>
          <div class="sidebar-footer" @click="$router.push('/profile')">
            <div class="user-profile">
              <el-avatar :size="32" :src="fullAvatarUrl" />
              <div class="user-texts">
                <span class="name">{{ currentUser.username || '加载中...' }}</span>
                <span class="status">在线 · 点击设置</span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- 2. 移动端抽屉：仅在手机端点击菜单后显示 -->
      <el-drawer v-model="mobileMenuVisible" direction="ltr" size="280px" :with-header="false" class="mobile-drawer">
        <div class="sidebar-content" style="height: 100%">
           <div class="sidebar-header">
            <el-button class="new-chat-btn" type="primary" @click="createNewChatAndClose" :icon="Plus">开启新对话</el-button>
          </div>
          <div class="session-list custom-scrollbar">
            <div v-for="s in sessions" :key="s.id" :class="['session-card', currentSessionId === s.id ? 'active' : '']" @click="switchSessionAndClose(s.id)">
              <el-icon class="session-icon"><ChatDotSquare /></el-icon>
              <div class="session-info">
                <span class="title">{{ s.title }}</span>
              </div>
              <el-icon class="delete-btn" @click.stop="deleteSession(s.id)"><Delete /></el-icon>
            </div>
          </div>
          <div class="sidebar-footer" @click="$router.push('/profile')">
            <div class="user-profile">
              <el-avatar :size="32" :src="fullAvatarUrl" />
              <span class="name">{{ currentUser.username }}</span>
            </div>
          </div>
        </div>
      </el-drawer>

      <!-- 3. 右侧主对话区 -->
      <main class="chat-main">
        <header class="main-header">
          <div class="header-left">
            <!-- 手机端才显示的菜单按钮 -->
            <el-button class="mobile-menu-btn" :icon="Menu" circle @click="mobileMenuVisible = true" />
            <div class="header-info">
              <span class="session-label">当前会话</span>
              <h3 class="current-title">{{ currentSessionTitle }}</h3>
            </div>
          </div>
          <el-button circle :icon="Refresh" @click="fetchHistory(currentSessionId)" />
        </header>

        <div class="message-wall custom-scrollbar" ref="messageBox">
          <!-- 欢迎页 -->
          <div v-if="chatHistory.length === 0" class="welcome-section">
            <div class="welcome-card">
              <div class="hero-icon">🚗</div>
              <h1>您好！我是交通法助手</h1>
              <div class="quick-tips">
                <div class="tip-item" @click="quickStart('饮酒驾驶如何处罚？')">🍺 酒驾处罚</div>
                <div class="tip-item" @click="quickStart('交通事故处理？')">🚑 事故处理</div>
              </div>
            </div>
          </div>

          <div v-for="(msg, index) in chatHistory" :key="index" :class="['msg-row', msg.role === 'user' ? 'is-user' : 'is-ai']">
            <div class="msg-bubble">
              <div class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
              <div v-if="msg.role === 'ai' && msg.sources?.length" class="source-container">
                <el-divider border-style="dashed" />
                <el-popover placement="top-start" title="法律依据" :width="300" trigger="click">
                  <template #reference><span class="source-trigger"><el-icon><Document /></el-icon> 查看原文</span></template>
                  <div class="source-popover-content">
                    <div v-for="(s, i) in msg.sources" :key="i" class="source-text-item"><b>依据 {{ i + 1 }}:</b> {{ s }}</div>
                  </div>
                </el-popover>
              </div>
            </div>
          </div>
          <div v-if="loading" class="msg-row is-ai">
            <div class="msg-bubble loading-bubble"><div class="typing-loader"></div><span>正在检索法规...</span></div>
          </div>
        </div>

        <footer class="input-container">
          <div class="input-wrapper">
            <el-input v-model="inputQuery" placeholder="输入问题..." type="textarea" :autosize="{ minRows: 1, maxRows: 5 }" resize="none" @keyup.enter.prevent="handleSend" />
            <el-button type="primary" circle @click="handleSend" :loading="loading" :icon="Top" />
          </div>
        </footer>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { Plus, ChatDotSquare, Delete, Refresh, Document, Top, Menu } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import request from '../api/request';
import MarkdownIt from 'markdown-it';

interface SessionItem { id: string; title: string; updated_at?: string; }
interface Message { role: 'user' | 'ai'; content: string; sources?: string[]; }

const router = useRouter();
const sessions = ref<SessionItem[]>([]);
const currentSessionId = ref('');
const chatHistory = ref<Message[]>([]);
const inputQuery = ref('');
const loading = ref(false);
const mobileMenuVisible = ref(false); // 手机端菜单开关
const messageBox = ref<HTMLElement | null>(null);
const currentUser = ref({ username: '', avatar: '' });

const md = new MarkdownIt({ html: true, linkify: true });

// 修正头像 URL
const fullAvatarUrl = computed(() => {
  if (!currentUser.value.avatar) return 'https://api.dicebear.com/7.x/avataaars/svg?seed=Felix';
  // 重点：不要写死 http://localhost，直接用相对路径，通过 Vite 代理访问
  return `${currentUser.value.avatar}?t=${Date.now()}`;
});

const currentSessionTitle = computed(() => sessions.value.find(i => i.id === currentSessionId.value)?.title || '新对话');

onMounted(async () => {
  try {
    const [userRes, sessRes] = await Promise.all([request.get('/v1/chat/me'), request.get('/v1/chat/sessions')]);
    currentUser.value = userRes.data;
    sessions.value = sessRes.data;
    if (sessions.value[0]) await switchSession(sessions.value[0].id); else createNewChat();
  } catch (e) { router.push('/login'); }
});

const fetchSessions = async () => { sessions.value = (await request.get('/v1/chat/sessions')).data; };

const fetchHistory = async (id: string) => {
  const res = await request.get(`/v1/chat/history/${id}`);
  chatHistory.value = res.data.map((m: any) => ({
    role: m.role, content: m.content, sources: typeof m.sources === 'string' ? JSON.parse(m.sources) : m.sources
  }));
  await scrollToBottom();
};

const switchSession = async (id: string) => { currentSessionId.value = id; await fetchHistory(id); };
const switchSessionAndClose = async (id: string) => { await switchSession(id); mobileMenuVisible.value = false; };

const createNewChat = () => { currentSessionId.value = `session_${Math.random().toString(36).substr(2, 9)}`; chatHistory.value = []; };
const createNewChatAndClose = () => { createNewChat(); mobileMenuVisible.value = false; };

const handleSend = async () => {
  if (!inputQuery.value.trim() || loading.value) return;
  const question = inputQuery.value.trim();
  const sid = currentSessionId.value;

  chatHistory.value.push({ role: 'user', content: question });
  inputQuery.value = '';
  loading.value = true;

  // 使用 reactive 解决跳字不灵敏问题
  const aiMsg = reactive<Message>({ role: 'ai', content: '', sources: [] });
  chatHistory.value.push(aiMsg);
  await scrollToBottom();

  try {
    const response = await fetch('/api/v1/chat/ask_stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
      body: JSON.stringify({ question, session_id: sid })
    });
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let lines = buffer.split("\n\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const payload = JSON.parse(line.replace("data:", "").trim());
        if (payload.type === 'sources') aiMsg.sources = payload.data;
        else if (payload.type === 'content') {
          aiMsg.content += payload.data;
          const box = messageBox.value;
          if (box) box.scrollTop = box.scrollHeight;
        }
      }
      await nextTick();
    }
    await fetchSessions();
  } catch (e) { ElMessage.error('连接中断'); } finally { loading.value = false; }
};

const quickStart = (t: string) => { inputQuery.value = t; handleSend(); };
const formatTime = (t?: string) => t ? new Date(t).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '刚刚';
const renderMarkdown = (t: string) => md.render(t);
const scrollToBottom = async () => { await nextTick(); if (messageBox.value) messageBox.value.scrollTop = messageBox.value.scrollHeight; };

const deleteSession = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定删除吗？');
    await request.delete(`/v1/chat/session/${id}`);
    await fetchSessions();
    if (currentSessionId.value === id) createNewChat();
  } catch (e) {}
};
</script>

<style scoped lang="scss">
.glass-provider { height: 100vh; width: 100vw; background: #eef2f7; display: flex; justify-content: center; align-items: center; position: relative; overflow: hidden; }
.bg-bubble { position: absolute; border-radius: 50%; filter: blur(80px); z-index: 0; }
.bubble-1 { width: 400px; height: 400px; background: rgba(64, 158, 255, 0.2); top: -100px; left: -100px; }
.bubble-2 { width: 500px; height: 500px; background: rgba(103, 194, 58, 0.15); bottom: -150px; right: -150px; }

.app-container {
  width: 96%; height: 94%; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(25px); 
  border: 1px solid rgba(255, 255, 255, 0.6); border-radius: 28px; display: flex; z-index: 1; overflow: hidden;
  @media (max-width: 768px) { width: 100%; height: 100%; border-radius: 0; }
}

.sidebar {
  width: 280px; background: rgba(255, 255, 255, 0.3); border-right: 1px solid rgba(0, 0, 0, 0.05);
  display: flex; flex-direction: column;
  &.desktop-only { @media (max-width: 768px) { display: none; } }
}

.sidebar-content {
  display: flex; flex-direction: column; padding: 24px 16px; width: 100%; height: 100%; box-sizing: border-box;
  .session-list { flex: 1; overflow-y: auto; }
  .new-chat-btn { width: 100%; margin-bottom: 20px; border-radius: 12px; }
  .sidebar-footer { margin-top: auto; padding: 15px; background: rgba(255,255,255,0.5); border-radius: 12px; cursor: pointer;
    .user-profile { display: flex; align-items: center; gap: 10px; .name { font-size: 13px; font-weight: bold; } }
  }
}

.chat-main { flex: 1; display: flex; flex-direction: column; position: relative; background: #fff; }
.main-header { 
  padding: 15px 20px; border-bottom: 1px solid rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center;
  .header-left { display: flex; align-items: center; gap: 15px; }
  .mobile-menu-btn { display: none; @media (max-width: 768px) { display: inline-flex; } }
  .current-title { margin: 0; font-size: 16px; @media (max-width: 768px) { font-size: 14px; } }
}

.message-wall { 
  flex: 1; padding: 30px 15% 120px 15%; overflow-y: auto; scroll-behavior: smooth;
  @media (max-width: 768px) { padding: 20px 15px 100px 15px; }
}

.msg-row { 
  display: flex; margin-bottom: 25px; 
  &.is-user { justify-content: flex-end; .msg-bubble { background: #409eff; color: #fff; border-radius: 18px 18px 4px 18px; } }
  &.is-ai { justify-content: flex-start; .msg-bubble { background: #f4f4f5; color: #333; border-radius: 18px 18px 18px 4px; } }
  .msg-bubble { max-width: 85%; padding: 12px 16px; line-height: 1.6; font-size: 14px; }
}

.input-container { 
  position: absolute; bottom: 20px; left: 15%; right: 15%; 
  @media (max-width: 768px) { left: 10px; right: 10px; bottom: 10px; }
  .input-wrapper { 
    background: #fff; border-radius: 15px; padding: 8px 12px; display: flex; align-items: flex-end; 
    box-shadow: 0 5px 20px rgba(0,0,0,0.1); border: 1px solid #eee;
    :deep(.el-textarea__inner) { border: none; box-shadow: none; font-size: 14px; }
  }
}

.session-card {
  padding: 10px; margin-bottom: 8px; border-radius: 10px; display: flex; align-items: center; gap: 10px; cursor: pointer; position: relative;
  &:hover { background: rgba(0,0,0,0.03); .delete-btn { opacity: 1; } }
  &.active { background: #e6f1fc; color: #409eff; }
  .title { font-size: 13px; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .delete-btn { opacity: 0; color: #f56c6c; font-size: 14px; }
}

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #ddd; border-radius: 10px; }
</style>