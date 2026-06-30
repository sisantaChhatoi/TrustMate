from collections.abc import AsyncIterator
from typing import cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool

from server.chatbot.llm import make_chat_llm
from server.models.chat import Message

_SYSTEM_PROMPT = (
    "You are a calm, non-alarmist fraud-safety assistant for an Indian scam-protection "
    "app. Someone messages you about a suspicious call or message.\n\n"
    "1. CAPTURE FIRST (mandatory): if the user's message contains ANY scam detail — a phone "
    "number, bank account, UPI id, amount, their city, who the caller claimed to be, or the "
    "kind of scam — you MUST call save_incident with those fields before replying, and again "
    "whenever new details appear. This is not optional.\n"
    "2. GROUND your advice with the search_fraud_knowledge tool. Never invent helpline numbers "
    "or reporting steps.\n"
    "3. Reply in the user's language. Default to Hindi or Hinglish (Roman-script Hindi) — users "
    "are Indian and usually more comfortable that way. Use plain English only when the user "
    "clearly writes in plain English; when unsure, prefer Hinglish. Mirror the user's script. "
    "Be brief and clear; don't dump a long checklist every turn.\n"
    "4. To fill gaps, ask for the key missing details (the number that called, the account/UPI "
    "they were told to pay, their city) together in ONE natural question. Settle with what you "
    "get within 2-3 clarifications — never re-ask the same field.\n"
    "5. Never ask the user for an OTP, PIN, password, or card number yourself. Reassure them "
    "that hanging up and reporting (1930 / cybercrime.gov.in) is the right move."
)

_MAX_TOOL_ROUNDS = 5


def to_lc_messages(messages: list[Message]) -> list[BaseMessage]:
    return [
        HumanMessage(m.message) if m.role == "user" else AIMessage(m.message)
        for m in messages
    ]


class ChatbotEngine:
    def __init__(self) -> None:
        self._llm: BaseChatModel | None = None

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = make_chat_llm()
        return self._llm

    async def stream_reply(
        self,
        history: list[BaseMessage],
        user_message: str,
        tools: list[BaseTool],
    ) -> AsyncIterator[str]:
        llm = self.llm.bind_tools(tools)
        by_name = {t.name: t for t in tools}
        messages: list[BaseMessage] = [
            SystemMessage(_SYSTEM_PROMPT),
            *history,
            HumanMessage(user_message),
        ]

        for _ in range(_MAX_TOOL_ROUNDS):
            gathered: AIMessageChunk | None = None
            async for raw in llm.astream(messages):
                chunk = cast(AIMessageChunk, raw)
                if isinstance(chunk.content, str) and chunk.content:
                    yield chunk.content
                gathered = chunk if gathered is None else gathered + chunk

            if gathered is None:
                return
            messages.append(gathered)
            if not gathered.tool_calls:
                return

            for call in gathered.tool_calls:
                tool = by_name.get(call["name"])
                result = (
                    await tool.ainvoke(call["args"])
                    if tool is not None
                    else f"unknown tool: {call['name']}"
                )
                messages.append(
                    ToolMessage(content=str(result), tool_call_id=call["id"])
                )
