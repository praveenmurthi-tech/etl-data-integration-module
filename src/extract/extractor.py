from __future__ import annotations
from typing import Iterator, Optional, Any
import logging
import os
from pathlib import Path
import polars as pl
from sqlalchemy import text
from sqlalchemy.engine import Engine
from pymongo import MongoClient
import pandas as pd
import uuid

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def write_chunk_to_file(
    df: pl.DataFrame,
    out_dir: str,
    customer: str,
    dataset: str,
    run_id: int,
    chunk_no: int,
    dst_engine,
    data_type: str,
    config_name: str
) -> str:
    os.makedirs(out_dir, exist_ok=True)

    file_name = f"{customer}_{dataset}_{run_id}_chunk{chunk_no}.parquet"
    file_path = Path(out_dir) / file_name
    df.write_parquet(file_path)

    from src.core import audit as audit_core
    audit_core.log_extracted_file(
        dst_engine,
        run_id=run_id,
        dataset=dataset,
        file_path=str(file_path),
        rows=len(df),
        chunk_no=chunk_no,
        data_type=data_type,
        config_name=config_name
    )
    return str(file_path)


def extract_chunks(
    engine: Engine,
    table: str,
    customer: str,
    dataset: str,
    run_id: int,
    dst_engine,
    data_type,
    config_name,
    out_dir: str = "data_lake",
    incremental_column: Optional[str] = None,
    last_value: Optional[Any] = None,
    chunksize: int = 50_000,
) -> Iterator[str]:
    """Extract SQL table in chunks (max 50k rows per file)."""
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

            # UUID fix
            for col in chunk.select_dtypes(include="object").columns:
                if chunk[col].apply(lambda x: isinstance(x, uuid.UUID)).any():
                    chunk[col] = chunk[col].astype(str)

            pl_df = pl.from_pandas(chunk)

            logger.info(
                "Extracted chunk #%d with %d rows from table %s",
                chunk_number,
                len(pl_df),
                table,
            )

            yield write_chunk_to_file(
                pl_df, out_dir, customer, dataset, run_id, chunk_number, dst_engine,data_type,config_name
            )


def extract_file_chunks(
    path: str,
    format: str,
    customer: str,
    dataset: str,
    run_id: int,
    dst_engine,
    data_type,
    config_name,
    out_dir: str = "data_lake",
    chunksize: int = 50_000,
) -> Iterator[str]:
    """Extract CSV/Excel file in chunks (max 50k rows per file)."""
    logger.info("Reading file source: %s | format=%s | chunksize=%d", path, format, chunksize)

    if format.lower() == "csv":
        df = pl.read_csv(path)
    elif format.lower() in ("excel", "xlsx"):
        import pandas as pd
        df = pl.DataFrame(pd.read_excel(path))
    else:
        raise ValueError(f"Unsupported file format: {format}")

    for i in range(0, df.height, chunksize):
        chunk_no = (i // chunksize) + 1
        pl_chunk = df.slice(i, chunksize)
        yield write_chunk_to_file(pl_chunk, out_dir, customer, dataset, run_id, chunk_no, dst_engine,data_type,config_name)


def extract_mongo(
    source_cfg,
    customer: str,
    dataset: str,
    run_id: int,
    dst_engine,
    data_type,
    config_name,
    out_dir: str = "data_lake",
    chunksize: int = 50_000,
) -> Iterator[str]:
    """Extract Mongo collection in chunks (max 50k rows per file)."""
    client = MongoClient(source_cfg.uri)
    db = client[source_cfg.database]
    coll = db[source_cfg.collection]

    cursor = coll.find({}, batch_size=chunksize)
    batch, chunk_no = [], 0

    for doc in cursor:
        doc.pop("_id", None)
        doc = {k: str(v) for k, v in doc.items()}
        batch.append(doc)

        if len(batch) >= chunksize:
            chunk_no += 1
            pl_df = pl.DataFrame(batch)
            yield write_chunk_to_file(pl_df, out_dir, customer, dataset, run_id, chunk_no, data_type,dst_engine,config_name)
            batch = []

    if batch:
        chunk_no += 1
        pl_df = pl.DataFrame(batch)
        yield write_chunk_to_file(pl_df, out_dir, customer, dataset, run_id, chunk_no, dst_engine,data_type,config_name)
