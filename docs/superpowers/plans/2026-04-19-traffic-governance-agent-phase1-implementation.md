# Traffic Governance Agent Phase1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stable phase1 demo loop for traffic governance chat: question -> tool call -> chat bubble with tool tag + embedded iframe report page.

**Architecture:** Keep the current `/v1/chat/ask_stream` SSE pipeline and `AgentService` orchestration. Standardize map and congestion tool outputs to a unified `iframe_report` schema with `/embed/report?type=...&data=...`. Render all report visuals in a new frontend embed page (with optional Gaode JS map canvas), while keeping existing session persistence unchanged so current-session history can replay iframe reports.

**Tech Stack:** FastAPI, SQLAlchemy, LangChain tools, Vue3 + Element Plus, MarkdownIt, AMap JS API 2.0.

---

## File Structure And Responsibilities

- Modify: `frontend/src/views/Chat.vue`
  - Update welcome copy + placeholder to traffic governance context.
  - Stop blanket iframe stripping, allow trusted local embed iframe HTML.
- Create: `frontend/src/views/EmbedReport.vue`
  - Decode query payload and render `congestion/route/nearby` report templates.
  - Optional AMap canvas rendering when key is configured.
- Modify: `frontend/src/router/index.ts`
  - Register `/embed/report` route.
- Modify: `backend/app/services/tool_service.py`
  - Add congestion tool output.
  - Convert route/nearby outputs to unified `display_type/tool_name/iframe_url`.
- Modify: `backend/app/services/agent_service.py`
  - Remove weather tool from default dispatch.
  - Render tool summary + tool chip + iframe HTML in stream.
- Modify: `backend/app/services/rag_service.py`
  - Keep compatibility for unified tool output fields when this path is used.
- Modify: `backend/app/core/prompts.py`
  - Update `AGENT_SYSTEM_PROMPT` to traffic governance + congestion-first tool routing.
- Create: `backend/tests/test_tool_report_payload.py`
  - Test payload encode/decode and report URL generation helper behavior.

---

### Task 1: Frontend Embed Route Skeleton

**Files:**
- Create: `frontend/src/views/EmbedReport.vue`
- Modify: `frontend/src/router/index.ts`
- Test: `npm run build`

- [ ] **Step 1: Add `/embed/report` route**
  - Register route component in router.
  - Do not require auth guard to avoid iframe interception.

- [ ] **Step 2: Add minimal `EmbedReport.vue` shell**
  - Parse `type` and `data` query parameters.
  - Show fallback state when payload missing/invalid.

- [ ] **Step 3: Build and verify compile**
  - Run: `npm run build`
  - Expected: build passes with new route component.

- [ ] **Step 4: Commit**
  - Run:
  ```bash
  git add frontend/src/router/index.ts frontend/src/views/EmbedReport.vue
  git commit -m "feat: add unified embed report route and shell page"
  ```

### Task 2: Embed Report Rendering And AMap Canvas

**Files:**
- Modify: `frontend/src/views/EmbedReport.vue`
- Test: `npm run build`

- [ ] **Step 1: Add typed renderer for 3 report kinds**
  - `type=congestion`: title, meta info, KPI cards, areas, causes, suggestions.
  - `type=route`: origin/destination, distance, duration, advice.
  - `type=nearby`: query summary and POI list.

- [ ] **Step 2: Add optional Gaode JS map canvas**
  - Read key from `import.meta.env.VITE_AMAP_WEB_KEY`.
  - If key exists and payload has coordinates, render map markers/polyline.
  - If key missing, render clean fallback text (no crash).

- [ ] **Step 3: Build and verify compile**
  - Run: `npm run build`
  - Expected: build passes; no type errors.

- [ ] **Step 4: Commit**
  - Run:
  ```bash
  git add frontend/src/views/EmbedReport.vue
  git commit -m "feat: render congestion route nearby embed reports with optional amap canvas"
  ```

### Task 3: Chat Page Report Display UX

**Files:**
- Modify: `frontend/src/views/Chat.vue`
- Test: `npm run build`

- [ ] **Step 1: Replace legal-themed welcome/placeholder copy**
  - Update greeting and suggestion prompts to traffic governance.
  - Update input placeholder to governance-oriented text.

- [ ] **Step 2: Adjust sanitizer strategy**
  - Keep old-history protection.
  - Allow trusted local iframe pattern (`/embed/report`) to render.
  - Continue blocking non-local iframe content.

- [ ] **Step 3: Add lightweight styles for tool chip + iframe block**
  - Ensure iframe fits chat bubble and mobile width.

- [ ] **Step 4: Build and verify compile**
  - Run: `npm run build`
  - Expected: build passes; chat component compiles.

- [ ] **Step 5: Commit**
  - Run:
  ```bash
  git add frontend/src/views/Chat.vue
  git commit -m "feat: update chat copy and enable trusted embed report iframe rendering"
  ```

### Task 4: Tool Output Unification And Congestion Tool

**Files:**
- Modify: `backend/app/services/tool_service.py`
- Create: `backend/tests/test_tool_report_payload.py`
- Test: `python -m pytest backend/tests/test_tool_report_payload.py -q`

- [ ] **Step 1: Add helper for report payload URL**
  - Encode report dict with urlsafe base64.
  - Return `/embed/report?type=...&data=...`.

- [ ] **Step 2: Refactor route/nearby tool returns**
  - Return fields: `text_data`, `tool_name`, `display_type`, `iframe_url`.
  - Include compact render payload (meta + map coordinates when available).

- [ ] **Step 3: Add `congestion_check` tool**
  - Rule/template-driven output only.
  - Return same unified schema and congestion report payload.

- [ ] **Step 4: Add focused tests for URL payload helpers**
  - Verify generated URL contains `type` and decodable `data`.

- [ ] **Step 5: Run tests**
  - Run: `python -m pytest backend/tests/test_tool_report_payload.py -q`
  - Expected: PASS.

- [ ] **Step 6: Commit**
  - Run:
  ```bash
  git add backend/app/services/tool_service.py backend/tests/test_tool_report_payload.py
  git commit -m "feat: unify tool report payloads and add congestion check tool"
  ```

### Task 5: Agent Stream Rendering For Tool Report

**Files:**
- Modify: `backend/app/services/agent_service.py`
- Test: `python -m py_compile backend/app/services/agent_service.py`

- [ ] **Step 1: Update tool registry**
  - Remove weather from default tools.
  - Add congestion tool.

- [ ] **Step 2: Handle unified report schema in stream**
  - On tool result with `display_type=iframe_report`, stream:
    - summary text
    - tool chip html
    - iframe html (`src=iframe_url`)
  - Keep timeout/`done` guard.

- [ ] **Step 3: Static compile check**
  - Run: `python -m py_compile backend/app/services/agent_service.py`
  - Expected: no syntax errors.

- [ ] **Step 4: Commit**
  - Run:
  ```bash
  git add backend/app/services/agent_service.py
  git commit -m "feat: stream unified tool-report iframe blocks in agent responses"
  ```

### Task 6: Prompt And Compatibility Cleanup

**Files:**
- Modify: `backend/app/core/prompts.py`
- Modify: `backend/app/services/rag_service.py`
- Test: `python -m py_compile backend/app/core/prompts.py backend/app/services/rag_service.py`

- [ ] **Step 1: Rewrite `AGENT_SYSTEM_PROMPT`**
  - Traffic governance positioning.
  - Explicit congestion-check trigger instruction.
  - Remove dependence on third-party native H5 pages.

- [ ] **Step 2: Align `rag_service` tool-result compatibility**
  - If unified schema appears, output same tool chip + iframe html path.

- [ ] **Step 3: Static compile check**
  - Run: `python -m py_compile backend/app/core/prompts.py backend/app/services/rag_service.py`
  - Expected: no syntax errors.

- [ ] **Step 4: Commit**
  - Run:
  ```bash
  git add backend/app/core/prompts.py backend/app/services/rag_service.py
  git commit -m "chore: align prompts and rag compatibility with iframe report schema"
  ```

### Task 7: End-To-End Verification

**Files:**
- Modify: `docs/superpowers/specs/2026-04-19-traffic-governance-agent-phase1-design.md` (optional notes only)
- Test: manual E2E checks

- [ ] **Step 1: Start services and run smoke checks**
  - Backend: run project backend dev command.
  - Frontend: run project frontend dev command.

- [ ] **Step 2: Verify required scenarios**
  - Enter `/chat`: blank new session.
  - Ask congestion question: summary + tool chip + iframe report appears.
  - Ask route and nearby: same unified mechanism.
  - Open old session: iframe report remains viewable.

- [ ] **Step 3: Final build checks**
  - Run:
  ```bash
  python -m py_compile backend/app/services/tool_service.py backend/app/services/agent_service.py backend/app/services/rag_service.py
  npm run build
  ```
  - Expected: all pass.

- [ ] **Step 4: Commit**
  - Run:
  ```bash
  git add -A
  git commit -m "feat: phase1 traffic governance agent with unified iframe report workflow"
  ```

