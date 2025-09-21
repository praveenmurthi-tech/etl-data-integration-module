from __future__ import annotations
from typing import List
import logging
import polars as pl
from sqlalchemy import MetaData, Table
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)

def upsert_df(engine: Engine, df: pl.DataFrame, target_table: str, key_columns: List[str], batch_size: int = 1000) -> int:
    """
    Upsert a Polars DataFrame into Postgres target_table using ON CONFLICT DO UPDATE.
    Uses batching to avoid exceeding parameter limits for large DataFrames.
    """
    if df.is_empty():
        logger.warning("No data to upsert into table '%s'. DataFrame is empty.", target_table)
        return 0

    try:
        logger.info(
            "Starting UPSERT into table '%s' | rows=%d | keys=%s",
            target_table, df.height, key_columns
        )

        # Reflect the target table from DB
        md = MetaData()
        table = Table(target_table, md, autoload_with=engine)

        # Convert Polars → list of dicts
        records = df.to_dicts()

        total = 0
        with engine.begin() as conn:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]

                stmt = insert(table).values(batch)

                # Build update set (all non-key columns)
                update_cols = {
                    c.name: getattr(stmt.excluded, c.name)
                    for c in table.columns if c.name not in key_columns
                }

                stmt = stmt.on_conflict_do_update(
                    index_elements=key_columns,
                    set_=update_cols
                )

                result = conn.execute(stmt)
                total += result.rowcount or 0

        logger.info(
            "UPSERT completed for table '%s' | total rows affected=%d | batch_size=%d",
            target_table, total, batch_size
        )
        return total

    except Exception:
        logger.exception("Failed UPSERT into table '%s'", target_table)
        raise
