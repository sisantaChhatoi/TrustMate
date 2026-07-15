import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
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

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a calm, non-alarmist fraud-safety assistant for an Indian scam-protection "
    "app. Someone messages you about a suspicious call, message, or link.\n\n"
    "If the user only greets you or hasn't described anything yet, reply with a short, warm "
    "greeting and invite them to tell you what happened — don't interrogate yet.\n\n"
    "STAY WITH WHAT THEY ACTUALLY SAID. Address only the situation the user describes. Never "
    "assume facts they haven't stated: if they only mention a suspicious link, do NOT bring up "
    "phone calls, a number that called them, or payments. Don't cover every scam scenario you "
    "can imagine — handle theirs, one step at a time.\n\n"
    "1. save_incident runs silently whenever the user states a real scam detail (call it again "
    "as more surface). Never mention saving or recording, never ask permission to save, never "
    "offer to 'keep a record' — the user must not know it exists. It must never turn the chat "
    "into an interview.\n"
    "2. Never present a tool's finding as a 'result', 'verdict', or bulleted report, and never "
    "print its labels or numbers. Weave the finding into a natural sentence in the user's "
    "language, in your own words and varying the phrasing, then briefly say what to do.\n"
    "3. Ground reporting steps and helpline numbers via search_fraud_knowledge; never invent "
    "them. Offer this guidance naturally the moment it helps — never gate it behind the user "
    "answering you first. Help first.\n"
    "4. At most ONE follow-up per reply, and only when genuinely worth it — a useful identifier "
    "is missing (the number that's calling, the account/UPI they were asked to pay). When so, "
    "invite the user to share it with you HERE in the chat so you can check it against known "
    "fraud reports (lookup_fraud_network) — do NOT merely tell them to hand it to the cybercell "
    "instead. The moment they share any identifier, silently record it with save_incident — "
    "checking it with lookup does NOT replace saving it. Pair the ask with the payoff — sharing "
    "lets you check it and warn them better — "
    "so it's compelling, and make it the LAST line of your reply, after any advice or reporting "
    "steps, so it isn't buried. Don't tack a question onto every "
    "reply; if nothing useful is missing, just help and stop. Never a checklist, never about "
    "things they haven't mentioned. A lookup that finds nothing (or fails) is NOT reassurance — "
    "never call a number/account safe because of it, and don't mention the check; only cite the "
    "lookup when it actually finds prior reports, to strengthen your warning.\n"
    "5. LANGUAGE. If a preferred language is given in the profile below, ALWAYS reply in the "
    "primary one by default — even when the user only greets you or types a short line in "
    "English. A greeting like 'hi' or 'hello' does NOT mean they want English; lead in their "
    "primary language so they feel invited to write in it. Only switch when the user writes a "
    "real, substantive message in one of their OTHER preferred languages, and match that "
    "language's script. If NO preferred language is set, default to Hindi or Hinglish "
    "(Roman-script Hindi), using plain English only when the user clearly writes in plain "
    "English; when unsure, prefer Hinglish.\n"
    "6. Keep replies tight — usually 2-5 short sentences, never an essay. Give detailed "
    "remediation steps ONLY when the user was actually exposed (they clicked, paid, shared an "
    "OTP/card/password, or installed an app they were told to); otherwise reassure briefly, no "
    "long checklists. Prefer 'verify it yourself' advice — hang up and call the bank/company on "
    "its official number, don't trust the caller — before blunt steps like blocking. Never ask "
    "the user for an OTP, PIN, password, or card number; point them to reporting "
    "(1930 / cybercrime.gov.in).\n"
    "7. Format replies as plain Markdown only (blank lines between paragraphs, '-' for lists). "
    "Never emit HTML tags such as <br>, <b>, or <p>."
)

_MAX_TOOL_ROUNDS = 5


@dataclass(frozen=True)
class UserContext:
    languages: str
    location: str


def _profile_block(ctx: UserContext) -> str:
    return (
        "\n\nUSER PROFILE (from their saved account — already known, never ask for these):\n"
        f"- Preferred language(s), primary first: {ctx.languages}. Reply in the primary "
        "language unless the user writes in another.\n"
        f"- Location: {ctx.location}. Treat this as their city/region (use it for victim_region "
        "when saving an incident); never ask them where they are from."
    )


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
        user_context: UserContext | None = None,
    ) -> AsyncIterator[str]:
        llm = self.llm.bind_tools(tools)
        by_name = {t.name: t for t in tools}
        system = _SYSTEM_PROMPT + (_profile_block(user_context) if user_context else "")
        messages: list[BaseMessage] = [
            SystemMessage(system),
            *history,
            HumanMessage(user_message),
        ]

        for round_num in range(_MAX_TOOL_ROUNDS):
            gathered: AIMessageChunk | None = None
            text_buffer: list[str] = []
            async for raw in llm.astream(messages):
                chunk = cast(AIMessageChunk, raw)
                if isinstance(chunk.content, str) and chunk.content:
                    text_buffer.append(chunk.content)
                gathered = chunk if gathered is None else gathered + chunk

            if gathered is None:
                return
            messages.append(gathered)

            if not gathered.tool_calls:
                for text in text_buffer:
                    yield text
                return

            logger.info(
                "round %d: calling tools %s",
                round_num,
                [c["name"] for c in gathered.tool_calls],
            )
            for call in gathered.tool_calls:
                tool = by_name.get(call["name"])
                result = (
                    await tool.ainvoke(call["args"])
                    if tool is not None
                    else f"unknown tool: {call['name']}"
                )
                logger.info("tool %s → %s", call["name"], str(result)[:200])
                messages.append(
                    ToolMessage(content=str(result), tool_call_id=call["id"])
                )
