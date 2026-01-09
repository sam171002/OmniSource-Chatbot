from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
DB_DIR = BASE_DIR / "db"
DB_DIR.mkdir(exist_ok=True)


EXCEL_DB_PATH = DB_DIR / "excel.db"
ANALYTICS_DB_PATH = DB_DIR / "analytics.db"


def get_excel_engine() -> Engine:
    return create_engine(f"sqlite:///{EXCEL_DB_PATH}", future=True)


def get_analytics_engine() -> Engine:
    return create_engine(f"sqlite:///{ANALYTICS_DB_PATH}", future=True)


def init_analytics_schema() -> None:
    engine = get_analytics_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    conversation_id TEXT,
                    user_query TEXT NOT NULL,
                    routed_source TEXT NOT NULL,
                    success INTEGER,
                    feedback INTEGER,
                    response_time_ms REAL,
                    feedback_text TEXT
                );
                """
            )
        )

        # Backwards-compatible migration: add feedback_text if missing
        try:
            conn.execute(
                text("ALTER TABLE queries ADD COLUMN feedback_text TEXT")
            )
        except Exception:
            # Column already exists or other benign migration issue
            pass



