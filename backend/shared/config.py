from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(_ENV_FILE)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "scamcall"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60 * 24 * 7
    chat_provider: str = "sarvam"
    chat_temperature: float = 0.3
    chat_history_limit: int = 6
    groq_chat_model: str = "llama-3.3-70b-versatile"
    sarvam_chat_model: str = "sarvam-30b"
    sarvam_base_url: str = "https://api.sarvam.ai/v1"

    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    retrieval_top_k: int = 4
    retrieval_min_score: float = 0.35

    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "neo4jlocal"
    neo4j_database: str = "neo4j"

    groq_api_key: str = ""
    sarvam_api_key: str = ""

    stt_provider: str = "sarvam"
    stt_language_code: str = "unknown"
    stt_model: str = "saaras:v3"
    stt_sample_rate: int = 16000

    expo_push_url: str = "https://exp.host/--/api/v2/push/send"
    test_notification_phone: str = "+917992463077"

    detector_model: str = "llama-3.3-70b-versatile"
    detector_threshold: float = 0.6
    detect_interval_seconds: float = 4.0
    transcript_window_seconds: float = 45.0
    min_transcript_chars: int = 40
    consecutive_positives: int = 2

    graph_rebuild_interval_hours: int = 6


settings = Settings()
