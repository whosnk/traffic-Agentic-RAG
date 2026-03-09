# ITQA 智能交通法规问答与出行规划 Agent 系统

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12-green.svg)
![Vue](https://img.shields.io/badge/Vue-3.0-4FC08D.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688.svg)

**ITQA (Intelligent Traffic Question-Answering)** 是一款专为**交通法规咨询**与**智能出行规划**打造的全栈 AI Agent 平台。

本项目突破了传统“知识库问答”的局限，采用目前业界前沿的 **Hybrid RAG（混合检索增强生成）** 结合 **Native Tool Calling（原生函数调用 Agent）** 架构。它不仅是一个能精准回答“GB 国标”与“交规法条”且**零幻觉**的法律顾问，还是一个能结合高德地图 API，为你提供实时路线、周边查询与天气播报的**生活助理**。

---

## 🌟 核心亮点 (Highlights)

### 1. 🧠 真·Agent 架构 (Native Tool Calling)
彻底告别了依靠正则匹配 JSON 的“伪路由”方式，全面接入 LangChain 的 `bind_tools` 能力。
*   **多维意图重构**：构建“意图重构专家” Prompt，完美解决指代消解与双向意图隔离（查法规 vs 查地图）。
*   **多步推理与综合总结**：Agent 能够在后台自动请求高德 API 获取静态地图、打车费、红绿灯数量、天气预报等数据，并以此为观测值（Observation）进行自然语言的二次总结。

### 2. 🛡️ 工业级防幻觉 RAG 体系 (Anti-Hallucination)
针对法律领域“容错率极低”的特性，构筑了三道坚固的防线：
*   **高召回漏斗**：使用 `PDFPlumberLoader` 精准解析国标文件的复杂双栏与表格。采用 **FAISS 稠密检索 (Top-40) + BM25 稀疏检索 (Top-20)** 的双路召回，不放过任何细微数字（如 `60km/h`）。
*   **Rerank 物理截断**：引入 `AliyunReranker`（gte-rerank），当重排得分低于严格阈值（如 `0.05`）时，物理切断大模型生成链路，从根源消除幻觉。
*   **CoT 适用范围校验**：通过思维链（Chain of Thought）提示词，教导模型进行“实体比对”。当用户询问“外星人酒驾”时，精准触发零假设原则，优雅拒答。

### 3. 🕸️ 知识图谱增强 (KG-RAG)
*   **实体关系抽取**：通过后台异步任务，利用 LLM 从法条中抽取 `(实体, 关系, 实体)` 三元组。
*   **图谱逻辑约束**：在 RAG 的生成阶段，将命中的因果逻辑链作为独立上下文喂给大模型，极大增强了模型对交通肇事因果推断的准确性，并在前端结合 ECharts 实现可视化图谱漫游。

### 4. 🎓 智能防作弊“每日一练”生成引擎
*   **千人千面**：根据用户 `UserQuizRecord`，自动过滤已做题目；题库不足时触发异步大模型出题。
*   **后置洗牌算法 (Shuffle)**：为克服大模型“Lazy LLM”（总是将正确答案放在 A 选项）的缺陷，在 Python 后端截获大模型生成的 JSON，动态剥离选项文本进行随机乱序重组，打造真实驾考级体验。

### 5. ⚡ 极致的全栈交互体验
*   **流式打字机**：基于 FastAPI 的 Generator 与前端 `Fetch API`，实现带有平滑渲染与乱码清洗（如过滤模型自带的 `<|DSML|>` 标记）的 SSE 流式输出。
*   **语义缓存 (Semantic Cache)**：基于 Redis 存储历史问答的向量，当新提问与历史提问的余弦相似度极高时，实现毫秒级缓存命中。
*   **BYOK 多租户**：支持用户在前端独立配置自己的 LLM / Embedding / Vision 模型的 API Key。

---

## 🛠️ 技术栈 (Tech Stack)

### 后端 (Backend)
*   **核心框架**: FastAPI, Python 3.12
*   **AI 层**: LangChain, OpenAI / DeepSeek (LLM), 阿里云通义 (Embedding & Reranker)
*   **检索与缓存**: FAISS, Rank-BM25, Redis
*   **数据库**: MySQL 8.0, SQLAlchemy ORM
*   **数据解析**: PDFPlumber, Jieba

### 前端 (Frontend)
*   **核心框架**: Vue 3 (Composition API), TypeScript, Vite
*   **UI 组件**: Element Plus, SCSS (全面支持移动端响应式)
*   **可视化**: ECharts (力导向图、饼图)
*   **多媒体**: Markdown-it (实时渲染), Web Speech API (语音识别与 TTS)

---

## 📂 核心架构全景图

```text
User Query
   │
   ├─► 1. 语义缓存检查 (Redis + Cosine Similarity) -> [命中则直接返回]
   │
   ├─► 2. 意图重构 (Intent Reconstruction via LLM)
   │
   ├─► 3. 智能 Agent 判定 (Tool Calling)
   │      ├─► 调用高德路线规划 API -> 返回综合总结与静态地图
   │      ├─► 调用高德 POI API -> 返回周边设施
   │      └─► 调用高德天气 API -> 返回实时天气预报
   │
   └─► 4. 混合 RAG 检索 (未命中工具时)
          ├─► FAISS 稠密检索 (Top-40)
          ├─► BM25 稀疏检索 (Top-20)
          ├─► Rerank 精排与分数截断 (防幻觉熔断机制)
          ├─► 知识图谱关联查询 (Graph Triples)
          └─► LLM 基于 CoT 逻辑校验生成最终回答
```

---

## 📸 功能模块展示 (Features)

### 1. 智能交通法律顾问 (Chatbot)
支持复杂的责任判定与罚款查询。采用严格的引用回溯机制，每一次回答必须带上 `[资料X]` 标签，前端提供点击展开原文的交互体验。支持语音录入与结果朗读。

### 2. 出行规划管家 (Travel Agent)
告诉系统“从玄武招商花园到新街口怎么去？”。系统将自动调用高德 API，在聊天流中**生成路线预览图**，并提供包含红绿灯、打车费预估、拥堵情况的精细化建议。

### 3. “每日一练”刷题中心 (Smart Quiz)
系统通过对知识库文档大块切片，随机“盲盒抽取”上下文生成高难度的情景分析选择题，前端提供沉浸式的刷题界面与计分系统。

### 4. 知识图谱与舆情大屏 (Graph & Analytics)
管理员专属控制台。支持一键将海量用户咨询通过 K-Means 算法进行无监督聚类，由 LLM 总结热点词云；同时提供交通法律实体之间（如“违法行为”与“处罚措施”）的互动式力导向图。

---

## 🚀 本地快速启动 (Quick Start)

### 1. 克隆项目与配置环境
```bash
git clone https://github.com/your-username/ITQA-System.git
cd ITQA-System
```

### 2. 后端部署
```bash
cd backend
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
# 请在项目根目录复制 .env.example 为 .env，并填入您的 MySQL、Redis 及高德 API Key。

# 3. 初始化数据库表结构
python init_db.py

# 4. 启动 FastAPI 服务
python main.py
# 服务将运行在 http://127.0.0.1:8000
```

### 3. 前端部署
```bash
cd frontend
# 1. 安装依赖
npm install

# 2. 启动 Vite 开发服务器
npm run dev
# 默认运行在 http://127.0.0.1:5173
```

---

## 📝 贡献与许可 (License)

本项目采用 [MIT License](LICENSE) 协议开源。欢迎任何关于代码优化、架构重构或是业务拓展的 PR（Pull Request）与 Issue！

