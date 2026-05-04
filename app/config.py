from __future__ import annotations

from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


class Settings(BaseSettings):
    notion_api_key: str = Field(alias="NOTION_API_KEY")
    notion_database_id: str = Field(alias="NOTION_DATABASE_ID")
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    slack_webhook_url: Optional[str] = Field(default=None, alias="SLACK_WEBHOOK_URL")

    model_api_base_url: str = Field(default="", alias="MODEL_API_BASE_URL")
    model_api_endpoint: str = Field(
        default="/v1/gateway/claude/v1/messages/",
        alias="MODEL_API_ENDPOINT",
    )
    model_name: str = Field(default="claude-sonnet-4-6", alias="MODEL_NAME")

    model_config = SettingsConfigDict(extra="ignore")

    @property
    def model_api_url(self) -> str:
        if not self.model_api_base_url:
            raise ValueError("MODEL_API_BASE_URL is required for the configured gateway.")
        return f"{self.model_api_base_url.rstrip('/')}/{self.model_api_endpoint.lstrip('/')}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
