from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class LlmConfig(BaseModel):
    provider: Literal["openai", "anthropic"] = "openai"
    model: str = "gpt-4o-mini"
    api_key_env: str = ""

    @model_validator(mode="after")
    def default_api_key_env(self) -> LlmConfig:
        if not self.api_key_env:
            self.api_key_env = (
                "OPENAI_API_KEY" if self.provider == "openai" else "ANTHROPIC_API_KEY"
            )
        return self

    def resolve_api_key(self) -> str:
        key = os.environ.get(self.api_key_env, "")
        if not key:
            raise EnvironmentError(
                f"LLM API key env var '{self.api_key_env}' is not set."
            )
        return key


class SearchConfig(BaseModel):
    provider: str = "brave"
    api_key_env: str = "SEARCH_API_KEY"

    def resolve_api_key(self) -> str | None:
        return os.environ.get(self.api_key_env) or None


class NotifyConfig(BaseModel):
    topics: list[str] = Field(default_factory=list)
    on: list[
        Literal["answer_changed", "breaking_change", "run_complete", "error"]
    ] = Field(default_factory=list)


class LinkEntry(BaseModel):
    label: str
    url: str


class AlternativeEntry(BaseModel):
    name: str
    links: list[str] = Field(default_factory=list)
    comment: str = ""


class GlobalConfig(BaseModel):
    llm: LlmConfig = Field(default_factory=LlmConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)
    questions: list[str] = Field(default_factory=list)
    instructions: str = ""


class ProjectConfig(BaseModel):
    name: str
    description: str = ""
    repo: str = ""
    homepage: str = ""
    changelog_url: str = ""
    links: list[LinkEntry] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    instructions: str = ""
    alternatives: list[AlternativeEntry] = Field(default_factory=list)
    notify: NotifyConfig | None = None
    llm: LlmConfig | None = None
