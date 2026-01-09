from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class IngestionResponse(BaseModel):
    pdf_chunks: int
    excel_rows: int


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    conversation_id: str
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    answer: str
    routed_source: Optional[str]
    citations: List[Dict[str, Any]]
    query_id: Optional[int] = None


class FeedbackRequest(BaseModel):
    query_id: int
    feedback: int  # +1 for up, -1 for down
    feedback_text: Optional[str] = None


class AnalyticsSummary(BaseModel):
    total_queries: int
    by_source: Dict[str, int]
    avg_response_time_ms: float
    feedback_summary: Dict[str, int]



