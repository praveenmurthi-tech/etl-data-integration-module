from __future__ import annotations
from typing import Dict, Iterable
import logging
import polars as pl
from datetime import datetime
from pymongo import MongoClient
from ..config import MONGO_URI, MONGO_DB

logger = logging.getLogger(__name__)

def map_columns(
    df: pl.DataFrame,
    mapping: Dict[str, str],
    required_columns: Iterable[str],
    customer_name: str,
    mongo_uri: str = None,
    mongo_db: str = None,
) -> pl.DataFrame:
    """
    One-to-one mapping: destination_col -> source_col.
    Pads missing destination columns with None.
    If mapping fails, dump raw DataFrame into MongoDB fallback.
    """
    try:
        logger.info("Starting column mapping | input_cols=%s | required_cols=%s",
                    df.columns, list(required_columns))

        out = pl.DataFrame()

        for dest_col, src_col in mapping.items():
            if src_col in df.columns:
                out = out.with_columns(df[src_col].alias(dest_col))
            else:
                logger.warning("Source column '%s' not found; filling destination '%s' with None",
                               src_col, dest_col)
                out = out.with_columns(pl.lit(None).alias(dest_col))

        # Ensure ordering & padding for required columns
        for col in required_columns:
            if col not in out.columns:
                logger.warning("Required destination column '%s' missing in mapping; padding with None", col)
                out = out.with_columns(pl.lit(None).alias(col))

        out = out.select(required_columns)

        logger.info("Column mapping completed | rows=%d | cols=%d", out.height, out.width)
        return out

    except Exception as e:
        logger.exception("Column mapping failed: %s", e)

        # Mongo fallback
        try:
            client = MongoClient(mongo_uri or MONGO_URI)
            db = client[mongo_db or MONGO_DB]

            coll_name = f"{customer_name}_{datetime.now().strftime('%Y%m%d')}"
            coll = db[coll_name]

            # Convert Polars → dict for Mongo
            records = out.to_dicts() if 'out' in locals() else df.to_dicts()
            if records:
                coll.insert_many(records)
                logger.info("✅ Fallback: Dumped %d records to MongoDB collection '%s.%s'",
                            len(records), db.name, coll_name)
            else:
                logger.warning("⚠️ Fallback: DataFrame empty, nothing to dump.")

        except Exception as mongo_err:
            logger.exception("MongoDB fallback also failed: %s", mongo_err)

        raise  # still raise the original mapping exception
