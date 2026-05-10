# EV Charge Route Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-stage "electric vehicle charging route planning" module that reuses the existing chat tool-call and iframe report workflow.

**Architecture:** Add one backend LangChain tool that uses the existing AMap route and coordinate helpers, then builds a rule-based EV charging plan using driving style, current SOC, reserve SOC, route distance, and route duration. Return the same `iframe_report` schema already used by congestion, route, and nearby tools. Extend `EmbedReport.vue` with `type=ev_charge` rendering and map support.

**Tech Stack:** FastAPI service layer, LangChain tools, Vue3, Element Plus project conventions, AMap REST/JS map integration.

---

## File Responsibilities

- Modify: `backend/app/services/tool_service.py`
  - Add EV charging route plan generator.
  - Add `agent_ev_charge_plan` tool.
- Modify: `backend/app/services/agent_service.py`
  - Register the EV tool and stream its iframe report.
- Modify: `backend/app/services/rag_service.py`
  - Register the EV tool in the compatibility path.
- Modify: `backend/app/core/prompts.py`
  - Tell the agent when to call `agent_ev_charge_plan`.
- Modify: `frontend/src/views/EmbedReport.vue`
  - Render `ev_charge` report data and map points.
- Modify: `frontend/src/views/Chat.vue`
  - Add one quick-start prompt for EV charging planning.
- Modify: `backend/tests/test_tool_report_payload.py`
  - Add a schema-level test for EV iframe payload output.

---

### Task 1: Backend EV Tool

- [ ] Add style coefficient mapping from the LLM project (`经济/效率/均衡/自定义`).
- [ ] Add rule-based charge stop generation.
- [ ] Add `ToolService.get_ev_charge_plan(...)`.
- [ ] Add `agent_ev_charge_plan` LangChain tool.
- [ ] Add a lightweight unit test for output schema.

### Task 2: Agent Wiring

- [ ] Import and register `agent_ev_charge_plan` in `AgentService`.
- [ ] Add EV status text in `_get_tool_status_text`.
- [ ] Import and register the tool in `RAGService` compatibility path.
- [ ] Update `AGENT_SYSTEM_PROMPT` tool routing rules.

### Task 3: Frontend Report

- [ ] Add `ev_charge` title support.
- [ ] Render route summary, EV inputs, charging plan, cost/wait estimates.
- [ ] Add EV markers to map collector.
- [ ] Add chat quick-start prompt.

### Task 4: Verification

- [ ] Run backend compile checks.
- [ ] Run `Agent` environment unittest.
- [ ] Run frontend build.
- [ ] Report exact test commands and outcomes.
