<template>
  <div class="landing-wrapper">
    <!-- 动态背景装饰 -->
    <div class="bg-blob blob-1"></div>
    <div class="bg-blob blob-2"></div>

    <div class="content-box">
      <header class="hero-section">
        <div class="logo-circle">智</div>
        <h1>交通治理决策智能体</h1>
        <p>像使用 AI 助手一样完成交通诊断、拥堵体检、治理方案生成与结果展示</p>
      </header>

      <!-- 功能导航网格：响应式适配 -->
      <div class="nav-grid">
        <!-- 1. 交通治理助手 -->
        <div class="nav-card" @click="$router.push('/chat')">
          <div class="card-icon chat-icon"><el-icon><ChatLineRound /></el-icon></div>
          <div class="card-body">
            <h3>智能对话工作台</h3>
            <p>基于自然语言完成交通问题分析、治理问答与任务分解</p>
          </div>
          <el-icon class="arrow"><ArrowRight /></el-icon>
        </div>

        <!-- 2. 城市拥堵体检 -->
        <div class="nav-card" @click="$router.push('/chat')">
          <div class="card-icon graph-icon"><el-icon><Share /></el-icon></div>
          <div class="card-body">
            <h3>城市拥堵体检</h3>
            <p>面向区域路网运行状态生成体检报告与重点问题识别</p>
          </div>
          <el-icon class="arrow"><ArrowRight /></el-icon>
        </div>

        <!-- 3. 仿真推演评估 -->
        <div class="nav-card" @click="$router.push('/chat')">
          <div class="card-icon quiz-icon"><el-icon><Edit /></el-icon></div>
          <div class="card-body">
            <h3>仿真推演评估</h3>
            <p>对候选治理策略进行情景推演与效果展示</p>
          </div>
          <el-icon class="arrow"><ArrowRight /></el-icon>
        </div>

        <!-- 4. 个人中心 -->
        <div class="nav-card" @click="$router.push('/profile')">
          <div class="card-icon profile-icon"><el-icon><User /></el-icon></div>
          <div class="card-body">
            <h3>个人中心</h3>
            <p>账户设置、模型偏好与平台使用管理</p>
          </div>
          <el-icon class="arrow"><ArrowRight /></el-icon>
        </div>
      </div>

      <footer class="landing-footer">
        <el-button link @click="handleLogout" :icon="SwitchButton">退出登录</el-button>
        <span class="version">v6.0 Stable</span>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { ChatLineRound, Share, User, ArrowRight, SwitchButton, Edit } from '@element-plus/icons-vue';

const router = useRouter();

const handleLogout = () => {
  localStorage.clear();
  router.push('/login');
};
</script>

<style scoped lang="scss">
.landing-wrapper {
  min-height: 100vh; width: 100vw; background: var(--ai-gradient-soft);
  display: flex; justify-content: center; align-items: center;
  position: relative; overflow-x: hidden; padding: 20px;
}

.bg-blob {
  position: absolute; border-radius: 50%; filter: blur(80px); z-index: 0; opacity: 0.5;
}
.blob-1 { width: 440px; height: 440px; background: rgba(37, 99, 235, 0.22); top: -120px; left: -120px; }
.blob-2 { width: 340px; height: 340px; background: rgba(124, 58, 237, 0.18); bottom: -60px; right: -60px; }

.content-box { z-index: 1; width: 100%; max-width: 980px; }

.hero-section {
  text-align: center; margin-bottom: 42px;
  .logo-circle { width: 70px; height: 70px; margin: 0 auto 18px; border-radius: 24px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 30px; font-weight: 900; background: var(--ai-gradient); box-shadow: var(--ai-shadow-glow); }
  h1 { font-size: 44px; color: var(--ai-text); margin: 0; font-weight: 900; letter-spacing: -0.05em; }
  p { color: var(--ai-text-muted); margin: 12px auto 0; max-width: 640px; line-height: 1.8; }
}

.nav-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px;
  @media (max-width: 600px) { grid-template-columns: 1fr; } /* 移动端单列 */
}

.nav-card {
  background: rgba(255, 255, 255, 0.84); backdrop-filter: blur(22px);
  border-radius: 24px; padding: 24px; cursor: pointer;
  display: flex; align-items: center; gap: 15px;
  transition: all 0.26s ease; border: 1px solid var(--ai-border);
  box-shadow: var(--ai-shadow-sm);

  &:hover {
    transform: translateY(-5px); background: #fff;
    box-shadow: var(--ai-shadow-md);
    .arrow { transform: translateX(5px); color: var(--ai-primary); }
  }

  .card-icon {
    width: 54px; height: 54px; border-radius: 16px;
    display: flex; align-items: center; justify-content: center; font-size: 24px;
    &.chat-icon { background: rgba(37,99,235,0.1); color: var(--ai-primary); }
    &.graph-icon { background: rgba(22,163,74,0.1); color: var(--ai-success); }
    &.profile-icon { background: rgba(100,116,139,0.1); color: var(--ai-text-muted); }
    &.quiz-icon { background: rgba(245,158,11,0.12); color: var(--ai-warning); }
  }

  .card-body {
    flex: 1;
    h3 { margin: 0; font-size: 17px; color: var(--ai-text); font-weight: 800; }
    p { margin: 6px 0 0; font-size: 12.5px; color: var(--ai-text-muted); line-height: 1.6; }
  }
  .arrow { color: #ccc; transition: 0.3s; }
}

.landing-footer {
  margin-top: 40px; display: flex; justify-content: space-between;
  font-size: 12px; color: var(--ai-text-soft);
}
</style>
