from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from .db import get_excel_engine


def ingest_social_listening(csv_path: Path, table_name: str = "social_listening") -> int:
    """
    Load the social listening CSV into SQLite using Pandas.
    Returns number of rows inserted.
    """
    df = pd.read_csv(csv_path)
    engine = get_excel_engine()

    with engine.begin() as conn:
        # Replace table on re-ingest
        df.to_sql(table_name, conn, if_exists="replace", index=False)

    return len(df)


def run_structured_query(natural_language_query: str, table_name: str = "social_listening") -> dict:
    """
    This function is intended to be called by an LLM-generated SQL.
    For safety and simplicity, we keep the API tiny and let routing build SQL.
    """
    raise NotImplementedError(
        "This function is a placeholder. SQL execution is handled in the LangGraph excel agent."
    )



