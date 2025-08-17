from __future__ import annotations
from typing import List
import logging
import pandas as pd
from sqlalchemy import MetaData, Table
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)

def upsert_df(engine: Engine, df: pd.DataFrame, target_table: str, key_columns: List[str]) -> int:
    """Upsert a DataFrame into Postgres target_table using ON CONFLICT DO UPDATE."""
    if df.empty:
        logger.warning("⚠️ No data to upsert into table '%s'. DataFrame is empty.", target_table)
        return 0

    try:
        logger.info("🚀 Starting UPSERT into table '%s' | rows=%d | keys=%s",
                    target_table, len(df), key_columns)

        md = MetaData()
        md.reflect(engine, only=[target_table])
        table = Table(target_table, md, autoload_with=engine)

        records = df.to_dict(orient="records")

        with engine.begin() as conn:
            stmt = insert(table).values(records)

            update_cols = {
                c.name: getattr(stmt.excluded, c.name)
                for c in table.columns if c.name not in key_columns
            }

            stmt = stmt.on_conflict_do_update(
                index_elements=key_columns,
                set_=update_cols
            )

            result = conn.execute(stmt)
            rowcount = result.rowcount or 0

        logger.info("✅ UPSERT completed for table '%s' | rows affected=%d", target_table, rowcount)
        return rowcount

    except Exception as e:
        logger.exception("❌ Failed UPSERT into table '%s'", target_table)
        raise
