import json
import logging

from groq import AsyncGroq
from groq.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from groq.types.chat.completion_create_params import (
    ResponseFormatResponseFormatJsonObject as JsonObjectFormat,
)
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("scamcall.detector")

_SYSTEM_PROMPT = """You are a fraud-detection assistant listening to a live phone \
call in Hindi, English, or Hinglish. Decide whether the conversation shows signs of \
a SCAM targeting the listener.

Watch for: requests for OTP/PIN/CVV, KYC-update pressure, account-blocking or \
arrest threats, fake bank/police/government impersonation, urgency, and pressure to \
pay or transfer money (UPI/links).

Respond with ONLY a JSON object, no prose:
{"scam": bool, "confidence": number 0..1, "reason": short string, "red_flags": [string]}

Judge intent as it builds across the transcript. Legitimate small talk is not a scam."""


class Detection(BaseModel):
    scam: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    red_flags: list[str] = Field(default_factory=list)


class ScamDetector:
    def __init__(
        self, api_key: str | None, *, model: str, threshold: float = 0.6
    ) -> None:
        self._client = AsyncGroq(api_key=api_key) if api_key else AsyncGroq()
        self._model = model
        self.threshold = threshold

    async def detect(self, transcript: str) -> Detection:
        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=_SYSTEM_PROMPT),
            ChatCompletionUserMessageParam(role="user", content=transcript),
        ]
        response_format = JsonObjectFormat(type="json_object")
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                temperature=0.0,
                response_format=response_format,
                messages=messages,
            )
            raw = completion.choices[0].message.content or "{}"
            return Detection.model_validate_json(raw)
        except (ValidationError, json.JSONDecodeError) as exc:
            logger.warning("detector returned unparsable output: %s", exc)
            return Detection()
        except Exception:
            logger.exception("detector call failed")
            return Detection()

    def flags(self, detection: Detection) -> bool:
        return detection.scam and detection.confidence >= self.threshold


class AlertPolicy:
    """Hysteresis: fire after N consecutive flagged windows, then re-arm."""

    def __init__(self, consecutive_required: int = 2) -> None:
        self._required = max(1, consecutive_required)
        self._streak = 0

    def update(self, flagged: bool) -> bool:
        self._streak = self._streak + 1 if flagged else 0
        if self._streak >= self._required:
            self._streak = 0
            return True
        return False
