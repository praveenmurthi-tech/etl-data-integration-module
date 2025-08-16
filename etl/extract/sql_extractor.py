from __future__ import annotations
from typing import Iterator, Optional, Any
import logging
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

def extract_chunks(
    engine: Engine,
    table: str,
    incremental_column: Optional[str] = None,
    last_value: Optional[str] = None,
    chunksize: int = 50_000,
) -> Iterator[pd.DataFrame]:
    """Yield DataFrames from a source table, optionally with incremental filtering."""
    base_sql = f"SELECT * FROM {table}"
    params = {}
    if incremental_column and last_value:
        base_sql += f" WHERE {incremental_column} > :last_value"
        params["last_value"] = last_value
    logger.info("Running extraction: %s", base_sql)
    with engine.connect() as conn:
        for chunk in pd.read_sql_query(text(base_sql), conn, params=params, chunksize=chunksize):
            yield chunk
