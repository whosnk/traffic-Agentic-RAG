import json
import logging
import re

from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.prompts import AGENT_SYSTEM_PROMPT
from app.models.chat import ChatMessage
from app.services.config_service import ConfigService
from app.services.tool_service import agent_get_route, agent_search_nearby, agent_get_weather

logger = logging.getLogger("AgentService")


class AgentService:
    def __init__(self, db, current_user=None):
        self.db = db
        self.current_user = current_user

        llm_cfg = ConfigService.get_active_config(db, "llm")
        if not llm_cfg:
            raise Exception("LLM 配置缺失")

        user_prefs = current_user.ai_preferences if (current_user and current_user.ai_preferences) else {}
        final_llm_model = user_prefs.get("llm_model") or llm_cfg.model_name
        final_llm_key = user_prefs.get("llm_key") or llm_cfg.api_key
        final_base_url = llm_cfg.base_url or settings.OPENAI_BASE_URL

        if not final_base_url and "deepseek" in final_llm_model.lower():
            final_base_url = "https://api.deepseek.com"

        self.tools = [agent_get_route, agent_search_nearby, agent_get_weather]
        self.llm = ChatOpenAI(
            model=final_llm_model,
            openai_api_key=final_llm_key,
            openai_api_base=final_base_url,
            temperature=0.3,
            streaming=True
        )
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _build_history_messages(self, session_id):
        rows = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.asc()).limit(10).all()

        messages = []
        for row in rows:
            if row.role == "user":
                messages.append(HumanMessage(content=row.content))
            elif row.role == "ai":
                clean_content = re.sub(r"<[^>]+>", " ", row.content or "")
                messages.append(AIMessage(content=clean_content))
        return messages

    def _get_tool_status_text(self, tool_name):
        if "route" in tool_name:
            return "🔄 **正在规划出行方案...**\n\n"
        if "nearby" in tool_name:
            return "🔄 **正在搜索周边设施...**\n\n"
        if "weather" in tool_name:
            return "🔄 **正在查询实时天气...**\n\n"
        return "🔄 **正在调用工具...**\n\n"

    async def chat_stream(self, query, session_id="default"):
        messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)]
        messages.extend(self._build_history_messages(session_id))
        messages.append(HumanMessage(content=query))

        agent_msg = await self.llm_with_tools.ainvoke(messages)

        if not agent_msg.tool_calls:
            full_answer = ""
            async for chunk in self.llm.astream(messages):
                content = chunk.content
                if not content:
                    continue
                full_answer += content
                yield json.dumps({"type": "content", "data": content}, ensure_ascii=False)

            yield json.dumps({"type": "done", "full_answer": full_answer}, ensure_ascii=False)
            return

        messages.append(agent_msg)

        for tool_call in agent_msg.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            yield json.dumps({"type": "content", "data": self._get_tool_status_text(tool_name)}, ensure_ascii=False)

            selected_tool = next((tool for tool in self.tools if tool.name == tool_name), None)
            if not selected_tool:
                messages.append(ToolMessage(content="工具不存在", tool_call_id=tool_call["id"]))
                continue

            try:
                tool_result_raw = await selected_tool.ainvoke(tool_args)
            except Exception as e:
                logger.error(f"tool call failed: {e}")
                messages.append(ToolMessage(content=f"工具调用失败: {str(e)}", tool_call_id=tool_call["id"]))
                continue

            tool_res_str = str(tool_result_raw)

            try:
                res_dict = json.loads(tool_res_str)
                if "html_widget" in res_dict and "text_data" in res_dict:
                    yield json.dumps({"type": "content", "data": res_dict["html_widget"] + "\n\n"}, ensure_ascii=False)
                    messages.append(ToolMessage(content=res_dict["text_data"], tool_call_id=tool_call["id"]))
                    continue
            except json.JSONDecodeError:
                pass

            messages.append(ToolMessage(content=tool_res_str, tool_call_id=tool_call["id"]))

        full_answer = ""
        async for chunk in self.llm.astream(messages):
            content = chunk.content
            if not content:
                continue
            clean_content = re.sub(r'<\|?DSML\|?.*?>', '', content, flags=re.IGNORECASE)
            clean_content = re.sub(r'</\|?DSML\|?.*?>', '', clean_content, flags=re.IGNORECASE)
            if not clean_content.strip():
                continue
            full_answer += clean_content
            yield json.dumps({"type": "content", "data": clean_content}, ensure_ascii=False)

        yield json.dumps({"type": "done", "full_answer": full_answer}, ensure_ascii=False)
