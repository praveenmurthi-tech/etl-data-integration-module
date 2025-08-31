from __future__ import annotations
from typing import Iterator, Optional, Any
import logging
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from pymongo import MongoClient


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Optional: Add a console handler if not already added
if not logger.hasHandlers():
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def extract_chunks(
    engine: Engine,
    table: str,
    incremental_column: Optional[str] = None,
    last_value: Optional[Any] = None,
    chunksize: int = 50_000,
) -> Iterator[pd.DataFrame]:
    """Yield DataFrames from a source table, optionally with incremental filtering."""

    # Quote identifiers to avoid SQL injection
    quoted_table = f'"{table}"'
    base_sql = f"SELECT * FROM {table}"

    params = {}
    if incremental_column and last_value is not None:
        base_sql += f' WHERE "{incremental_column}" > :last_value'
        params["last_value"] = last_value

    logger.info("Running extraction: %s | params=%s", base_sql, params)

    chunk_number = 0
    with engine.connect() as conn:
        for chunk in pd.read_sql_query(text(base_sql), conn, params=params, chunksize=chunksize):
            chunk_number += 1
            logger.info(
                "Extracted chunk #%d with %d rows from table %s", 
                chunk_number, 
                len(chunk), 
                table
            )
            yield chunk


def extract_file_chunks(path: str, format: str = "csv", chunksize: int = 50_000) -> Iterator[pd.DataFrame]:
    """Yield DataFrames from a CSV/Excel file in chunks."""
    logger.info("Reading file source: %s | format=%s | chunksize=%d", path, format, chunksize)

    if format.lower() == "csv":
        for chunk in pd.read_csv(path, chunksize=chunksize):
            yield chunk

    elif format.lower() in ("excel", "xlsx"):
        # pandas read_excel doesn’t support chunksize directly, so read all then yield
        df = pd.read_excel(path)
        for i in range(0, len(df), chunksize):
            yield df.iloc[i:i+chunksize]

    else:
        raise ValueError(f"Unsupported file format: {format}")


def extract_mongo(source_cfg, chunksize: int = 50000):
    client = MongoClient(source_cfg.uri)
    db = client[source_cfg.database]
    coll = db[source_cfg.collection]

    cursor = coll.find({}, batch_size=chunksize)

    batch = []
    for doc in cursor:
        # Drop Mongo's internal _id and convert all fields to string
        doc.pop("_id", None)
        doc = {k: str(v) for k, v in doc.items()}
        batch.append(doc)

        if len(batch) >= chunksize:
            yield pd.DataFrame(batch)
            batch = []

    if batch:
        yield pd.DataFrame(batch)
