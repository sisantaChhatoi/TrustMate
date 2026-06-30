from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

from shared.config import settings


def make_chat_llm() -> BaseChatModel:
    provider = settings.chat_provider
    if provider == "sarvam":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.sarvam_chat_model,
            base_url=settings.sarvam_base_url,
            api_key=SecretStr(settings.sarvam_api_key),
            temperature=settings.chat_temperature,
        )
    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.groq_chat_model,
            temperature=settings.chat_temperature,
        )
    raise ValueError(f"unknown chat provider: {provider!r}")
