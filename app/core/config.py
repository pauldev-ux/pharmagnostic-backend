from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "testing", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    APP_NAME: str = Field(default="PHARMAGNOSTIC AI")
    APP_ENV: Environment = Field(default="development")
    APP_DEBUG: bool = Field(default=True)
    API_V1_PREFIX: str = Field(default="/api/v1")

    DATABASE_URL: str = Field(default="postgresql+psycopg://postgres:123456@localhost:5432/pharmagnostic_ai")
    DATABASE_HOST: str = Field(default="localhost")
    DATABASE_PORT: int = Field(default=5432)
    DATABASE_NAME: str = Field(default="pharmagnostic_ai")
    DATABASE_USER: str = Field(default="postgres")
    DATABASE_PASSWORD: str = Field(default="123456")

    FRONTEND_URL: str = Field(default="http://localhost:5173")
    SECRET_KEY: str = Field(default="change-this-secret-key")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Audio clínico y transcripción
    AUDIO_STORAGE_DIR: str = Field(default="storage/audios")
    AUDIO_ALLOWED_FORMATS: str = Field(default="webm,wav,mp3,ogg,m4a,mpeg")
    WHISPER_MODEL: str = Field(default="base")
    WHISPER_DEVICE: str = Field(default="cpu")
    WHISPER_COMPUTE_TYPE: str = Field(default="int8")

    # Base farmacológica + RAG (Ollama)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_EMBEDDING_MODEL: str = Field(default="nomic-embed-text")
    OLLAMA_CHAT_MODEL: str = Field(default="llama3")
    RAG_CHUNK_SIZE: int = Field(default=800)
    RAG_CHUNK_OVERLAP: int = Field(default=120)
    RAG_TOP_K: int = Field(default=5)
    RAG_MIN_SIMILARITY: float = Field(default=0.15)
    PHARMACOLOGICAL_FILES_PATH: str = Field(default="storage/pharmacological")
    PHARMACOLOGICAL_ALLOWED_FORMATS: str = Field(default="pdf,txt,docx")

    INITIAL_ADMIN_NAME: str = Field(default="Administrador")
    INITIAL_ADMIN_LAST_NAME: str = Field(default="Principal")
    INITIAL_ADMIN_EMAIL: str = Field(default="admin@pharmagnostic.com")
    INITIAL_ADMIN_USERNAME: str = Field(default="admin")
    INITIAL_ADMIN_PASSWORD: str = Field(default="123456")

    @model_validator(mode="after")
    def validate_database_config(self):
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+psycopg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
                f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            )
        else:
            db_url = self.DATABASE_URL.strip()
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
            elif db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
            self.DATABASE_URL = db_url
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
