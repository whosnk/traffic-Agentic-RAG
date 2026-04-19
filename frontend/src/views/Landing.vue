<template>
  <div class="landing-wrapper">
    <!-- 动态背景装饰 -->
    <div class="bg-blob blob-1"></div>
    <div class="bg-blob blob-2"></div>

    <div class="content-box">
      <header class="hero-section">
        <div class="logo-circle">🚗</div>
        <h1>交通决策治理智能体</h1>
        <p>通过自然语言交互完成交通诊断、拥堵体检、方案生成与结果展示</p>
      </header>

      <!-- 功能导航网格：响应式适配 -->
      <div class="nav-grid">
        <!-- 1. 交通治理助手 -->
        <div class="nav-card" @click="$router.push('/chat')">
          <div class="card-icon chat-icon"><el-icon><ChatLineRound /></el-icon></div>
          <div class="card-body">
            <h3>交通治理助手</h3>
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
  min-height: 100vh; width: 100vw; background: #f4f7f9;
  display: flex; justify-content: center; align-items: center;
  position: relative; overflow-x: hidden; padding: 20px;
}

.bg-blob {
  position: absolute; border-radius: 50%; filter: blur(80px); z-index: 0; opacity: 0.5;
}
.blob-1 { width: 400px; height: 400px; background: #409eff; top: -100px; left: -100px; }
.blob-2 { width: 300px; height: 300px; background: #67c23a; bottom: -50px; right: -50px; }

.content-box { z-index: 1; width: 100%; max-width: 800px; }

.hero-section {
  text-align: center; margin-bottom: 40px;
  .logo-circle { font-size: 40px; margin-bottom: 10px; }
  h1 { font-size: 28px; color: #333; margin: 0; font-weight: 800; }
  p { color: #888; margin-top: 5px; }
}

.nav-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;
  @media (max-width: 600px) { grid-template-columns: 1fr; } /* 移动端单列 */
}

.nav-card {
  background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(10px);
  border-radius: 20px; padding: 20px; cursor: pointer;
  display: flex; align-items: center; gap: 15px;
  transition: all 0.3s ease; border: 1px solid rgba(255,255,255,0.5);
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);

  &:hover {
    transform: translateY(-5px); background: #fff;
    box-shadow: 0 12px 24px rgba(0,0,0,0.08);
    .arrow { transform: translateX(5px); color: #409eff; }
  }

  .card-icon {
    width: 50px; height: 50px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center; font-size: 24px;
    &.chat-icon { background: #e6f1fc; color: #409eff; }
    &.graph-icon { background: #f0f9eb; color: #67c23a; }
    &.profile-icon { background: #f4f4f5; color: #909399; }
    &.quiz-icon { background: #fdf5e6; color: #ff9800; }
  }

  .card-body {
    flex: 1;
    h3 { margin: 0; font-size: 16px; color: #333; }
    p { margin: 4px 0 0; font-size: 12px; color: #999; line-height: 1.4; }
  }
  .arrow { color: #ccc; transition: 0.3s; }
}

.landing-footer {
  margin-top: 40px; display: flex; justify-content: space-between;
  font-size: 12px; color: #bbb;
}
</style>
