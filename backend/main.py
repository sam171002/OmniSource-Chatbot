from __future__ import annotations

import traceback
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .db import DATA_DIR, init_analytics_schema, get_analytics_engine
from .excel_ingestion import ingest_social_listening
from .graph import run_omni_graph
from .models import (
    AnalyticsSummary,
    ChatRequest,
    ChatResponse,
    IngestionResponse,
    FeedbackRequest,
)
from .pdf_ingestion import ingest_pdfs
from sqlalchemy import text


app = FastAPI(title="OmniSource Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    init_analytics_schema()
    # Clear analytics data for per-session counting
    engine = get_analytics_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM queries"))
    # Auto-ingest bundled data if present
    pdf_paths = []
    for name in ["omnisource_1.pdf", "omnisource_2.pdf"]:
        p = DATA_DIR / name
        if p.exists():
            pdf_paths.append(p)
    if pdf_paths:
        ingest_pdfs(pdf_paths)

    csv_path = DATA_DIR / "social-listening.csv"
    if csv_path.exists():
        ingest_social_listening(csv_path)


@app.post("/ingest", response_model=IngestionResponse)
def ingest_all():
    pdf_paths = []
    for name in ["omnisource_1.pdf", "omnisource_2.pdf"]:
        p = DATA_DIR / name
        if p.exists():
            pdf_paths.append(p)
    pdf_chunks = ingest_pdfs(pdf_paths) if pdf_paths else 0

    csv_path = DATA_DIR / "social-listening.csv"
    excel_rows = ingest_social_listening(csv_path) if csv_path.exists() else 0

    return IngestionResponse(pdf_chunks=pdf_chunks, excel_rows=excel_rows)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = run_omni_graph(
            conversation_id=req.conversation_id,
            history=[m.dict() for m in req.messages],
        )
        return ChatResponse(**result)
    except Exception as e:
        error_msg = f"Chat error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Log to console
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    engine = get_analytics_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE queries "
                "SET feedback = :fb, feedback_text = :fb_text "
                "WHERE id = :qid"
            ),
            dict(fb=req.feedback, fb_text=req.feedback_text, qid=req.query_id),
        )
    return {"status": "ok"}


@app.get("/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary():
    engine = get_analytics_engine()
    with engine.begin() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM queries")).scalar_one()
        by_source_rows = conn.execute(
            text(
                "SELECT routed_source, COUNT(*) AS c FROM queries "
                "GROUP BY routed_source"
            )
        ).fetchall()
        by_source: Dict[str, int] = {r[0] or "unknown": r[1] for r in by_source_rows}
        avg_rt = conn.execute(
            text("SELECT AVG(response_time_ms) FROM queries")
        ).scalar()
        fb_rows = conn.execute(
            text(
                "SELECT feedback, COUNT(*) FROM queries "
                "WHERE feedback IS NOT NULL "
                "GROUP BY feedback"
            )
        ).fetchall()

    feedback_summary: Dict[str, int] = {
        "up": 0,
        "down": 0,
    }
    for fb, count in fb_rows:
        if fb is None:
            continue
        if fb > 0:
            feedback_summary["up"] += count
        elif fb < 0:
            feedback_summary["down"] += count

    return AnalyticsSummary(
        total_queries=int(total or 0),
        by_source=by_source,
        avg_response_time_ms=float(avg_rt or 0.0),
        feedback_summary=feedback_summary,
    )



