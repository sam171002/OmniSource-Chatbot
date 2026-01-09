from __future__ import annotations

import time
from datetime import datetime
from typing import Annotated, Dict, List, Literal, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from sqlalchemy import text

from .db import get_excel_engine, get_analytics_engine
from .llm import chat_completion
from .pdf_ingestion import pdf_semantic_search


class OmniState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    routing_decision: Optional[Literal["pdf", "excel", "both"]]
    retrieval_context: Optional[str]
    citations: List[Dict]
    routed_source: Optional[str]
    start_time: float


ROUTER_SYSTEM_PROMPT = """
You are a routing controller for an analytics chatbot.
Decide the best primary source for answering the user's question:
- 'excel' for numeric, tabular, or metric-oriented questions about social listening, KPIs, or statistics.
- 'pdf' for conceptual, policy, or long-form document questions.
- 'both' if you clearly need quantitative evidence from Excel and narrative context from PDFs.

Answer with a single word: excel, pdf, or both.
"""


def _router_node(state: OmniState) -> OmniState:
    last_user_msg = [m for m in state["messages"] if isinstance(m, HumanMessage)][-1]
    route = chat_completion(
        ROUTER_SYSTEM_PROMPT,
        [{"role": "user", "content": last_user_msg.content}],
    ).strip().lower()
    if route not in {"excel", "pdf", "both"}:
        route = "pdf"
    state["routing_decision"] = route  # type: ignore[assignment]
    state["routed_source"] = route
    return state


def _pdf_retriever_node(state: OmniState) -> OmniState:
    last_user_msg = [m for m in state["messages"] if isinstance(m, HumanMessage)][-1]
    result = pdf_semantic_search(last_user_msg.content, k=5)
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]

    context_parts = []
    citations: List[Dict] = []
    for doc, meta in zip(docs, metas):
        file_name = meta.get("file_name")
        page = meta.get("page")
        context_parts.append(f"[{file_name}, page {page}]\n{doc}")
        citations.append(
            {
                "source_type": "pdf",
                "file_name": file_name,
                "page": page,
            }
        )

    if context_parts:
        state["retrieval_context"] = "\n\n".join(context_parts)
        state["citations"].extend(citations)
    return state


EXCEL_SQL_SYSTEM_PROMPT = """
You translate natural language questions into safe SQL queries for a SQLite database.

Database:
- Single table: social_listening
- Columns (case sensitive):
  - ProductModelName (TEXT)
  - ProductCategory (TEXT)              -- e.g. 'Smart Phone', 'Laptop', 'Tablet', 'TV'
  - ProductPrice (REAL)                 -- numeric price
  - RetailerName (TEXT)                 -- e.g. 'Bestbuy', 'Walmart'
  - RetailerZip (REAL)
  - RetailerCity (TEXT)
  - RetailerState (TEXT)
  - ProductOnSale (TEXT: 'Yes' or 'No')
  - ManufacturerName (TEXT)
  - ManufacturerRebate (TEXT: 'Yes' or 'No')
  - UserID (TEXT)
  - UserAge (REAL)
  - UserGender (TEXT)
  - UserOccupation (TEXT)
  - ReviewRating (REAL)
  - ReviewDate (TEXT)
  - ReviewText (TEXT)
  - sentiment (TEXT)
  - problem (TEXT)
  - about (TEXT)
  - keywords (TEXT)

Rules:
- Only output a single valid SQLite SELECT statement, nothing else.
- Never modify data (no INSERT/UPDATE/DELETE).
- Use WHERE filters that match the natural language (e.g. retailer, category, etc.).
- For aggregations like averages, use SQL functions such as AVG, COUNT, etc.
- If the question truly cannot be answered from this schema, return exactly:
  SELECT 'NO_ANSWER' AS note;

Examples:
- Q: What is the average price of all Smart Phone models sold by Bestbuy?
  SQL: SELECT AVG(ProductPrice) AS avg_price FROM social_listening WHERE ProductCategory = 'Smart Phone' AND RetailerName = 'Bestbuy';

- Q: How many Laptop products are sold by Walmart?
  SQL: SELECT COUNT(*) AS laptop_count FROM social_listening WHERE ProductCategory = 'Laptop' AND RetailerName = 'Walmart';

- Q: What is the average review rating for Samsung TVs?
  SQL: SELECT AVG(ReviewRating) AS avg_rating FROM social_listening WHERE ProductCategory = 'TV' AND ManufacturerName = 'Samsung';

Follow the same style for any other question and only output the final SQL query.
"""


def _excel_agent_node(state: OmniState) -> OmniState:
    last_user_msg = [m for m in state["messages"] if isinstance(m, HumanMessage)][-1]
    nl = last_user_msg.content
    sql = chat_completion(
        EXCEL_SQL_SYSTEM_PROMPT,
        [{"role": "user", "content": nl}],
    ).strip()

    # Safety: only allow SELECT
    if not sql.lower().startswith("select"):
        sql = "SELECT 'NO_ANSWER' AS note;"

    engine = get_excel_engine()
    rows = []
    columns: List[str] = []
    with engine.begin() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, r)) for r in result.fetchall()]

    if len(rows) == 1 and rows[0].get("note") == "NO_ANSWER":
        table_text = "No structured answer available from Excel for this question."
    else:
        # Simple text table representation for the LLM
        header = " | ".join(columns)
        sep = " | ".join(["---"] * len(columns))
        body_lines = []
        for r in rows[:50]:
            body_lines.append(" | ".join(str(r.get(c, "")) for c in columns))
        table_text = header + "\n" + sep + "\n" + "\n".join(body_lines)

    context = f"Structured result from Excel (table social_listening):\n{table_text}"
    prev = state.get("retrieval_context")
    state["retrieval_context"] = (prev + "\n\n" + context) if prev else context
    state["citations"].append(
        {
            "source_type": "excel",
            "table": "social_listening",
            "note": "SQLite query result",
        }
    )
    return state


ANSWER_SYSTEM_PROMPT = """
You are OmniSource, a multi-source analytics assistant.
You have access to:
- Structured social listening data from Excel (SQL query results).
- Long-form PDF documents.

Guidelines:
- Use the provided retrieval context as factual grounding; do not invent data.
- If information is missing, say you are not sure and propose what additional data is needed.
- Maintain conversational, concise answers.
- When answering questions that involve structured data from Excel, first provide a short natural language summary and then include a clear table of the most relevant rows (up to 10) in markdown format.
- When you cite sources, clearly indicate PDF file and page or Excel table.
"""


def _answer_node(state: OmniState) -> OmniState:
    last_user_msg = [m for m in state["messages"] if isinstance(m, HumanMessage)][-1]
    retrieval_context = state.get("retrieval_context") or "No external context."
    citations = state.get("citations", [])

    prompt = (
        f"User question:\n{last_user_msg.content}\n\n"
        f"Retrieved context:\n{retrieval_context}\n\n"
        f"Available citations metadata:\n{citations}\n\n"
        "Now answer the question. At the end, add a 'Sources:' section listing each source "
        "in the form 'PDF: <file>, page <n>' or 'Excel: social_listening table'."
    )

    answer_text = chat_completion(
        ANSWER_SYSTEM_PROMPT,
        [{"role": "user", "content": prompt}],
    )
    state["messages"].append(AIMessage(content=answer_text))
    return state


def _log_analytics(state: OmniState, conversation_id: str) -> int:
    engine = get_analytics_engine()
    now = datetime.utcnow().isoformat()
    routed_source = state.get("routed_source") or "unknown"
    duration_ms = max(0.0, (time.time() - state.get("start_time", time.time())) * 1000.0)

    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO queries (timestamp, conversation_id, user_query, routed_source,
                                     success, feedback, response_time_ms)
                VALUES (:ts, :cid, :q, :src, :success, :feedback, :rt)
                """
            ),
            dict(
                ts=now,
                cid=conversation_id,
                q=_get_last_user_text(state),
                src=routed_source,
                success=None,
                feedback=None,
                rt=duration_ms,
            ),
        )
        query_id = getattr(result, "lastrowid", None)
        if not query_id:
            query_id = conn.execute(text("SELECT last_insert_rowid()")).scalar_one()

    return int(query_id or 0)


def _get_last_user_text(state: OmniState) -> str:
    users = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    return users[-1].content if users else ""


def build_graph():
    graph = StateGraph(OmniState)

    graph.add_node("router", _router_node)
    graph.add_node("pdf_retriever", _pdf_retriever_node)
    graph.add_node("excel_agent", _excel_agent_node)
    graph.add_node("answer", _answer_node)

    graph.set_entry_point("router")

    def route_decision(state: OmniState):
        decision = state.get("routing_decision") or "pdf"
        if decision == "pdf":
            return "pdf_retriever"
        if decision == "excel":
            return "excel_agent"
        if decision == "both":
            # For "both", start with PDF retriever, then excel will be called after
            return "pdf_retriever"
        return "pdf_retriever"

    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "pdf_retriever": "pdf_retriever",
            "excel_agent": "excel_agent",
        },
    )

    # After PDF retriever, check if we need Excel too
    def after_pdf(state: OmniState):
        decision = state.get("routing_decision") or "pdf"
        if decision == "both":
            return "excel_agent"
        return "answer"

    graph.add_conditional_edges(
        "pdf_retriever",
        after_pdf,
        {
            "excel_agent": "excel_agent",
            "answer": "answer",
        },
    )

    # After retrievers, always go to answer
    graph.add_edge("excel_agent", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


def run_omni_graph(conversation_id: str, history: List[Dict]) -> Dict:
    """
    history: list of {"role": "user"|"assistant", "content": str}
    Returns: {"answer": str, "routed_source": str, "citations": list, "query_id": int}
    """
    messages: List[BaseMessage] = []
    for m in history:
        if m["role"] == "user":
            messages.append(HumanMessage(content=m["content"]))
        else:
            messages.append(AIMessage(content=m["content"]))

    workflow = build_graph()
    initial_state: OmniState = {
        "messages": messages,
        "routing_decision": None,
        "retrieval_context": None,
        "citations": [],
        "routed_source": None,
        "start_time": time.time(),
    }

    final_state = workflow.invoke(initial_state)
    query_id = _log_analytics(final_state, conversation_id)

    answer_msg = [m for m in final_state["messages"] if isinstance(m, AIMessage)][-1]
    return {
        "answer": answer_msg.content,
        "routed_source": final_state.get("routed_source"),
        "citations": final_state.get("citations", []),
        "query_id": query_id,
    }



