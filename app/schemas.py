from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ParseJobRequest(BaseModel):
    url: HttpUrl


class ExtractedJob(BaseModel):
    company_name: str = Field(description="기업명")
    role: str = Field(description="직군")
    platform: Optional[str] = Field(default=None, description="채용 플랫폼")
    deadline: Optional[str] = Field(default=None, description="YYYY-MM-DD date or null")
    keywords: List[str] = Field(default_factory=list)
    memo: Optional[str] = None
    interview_questions: Optional[str] = None
    source_url: str


class ParseJobResponse(BaseModel):
    job: ExtractedJob
    notion_page_id: str
