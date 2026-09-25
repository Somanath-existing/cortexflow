from pydantic import BaseModel
from typing import Optional, Any


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict] = []
    chart_data: Optional[Any] = None


class DocumentUpload(BaseModel):
    title: str
    content: str
    doc_type: str = "report"


class AnalyticsRequest(BaseModel):
    metric: str
    region: Optional[str] = None
    quarter: Optional[str] = None
    year: Optional[int] = None
