from __future__ import annotations
from typing import Dict, Iterable
import logging
import pandas as pd

logger = logging.getLogger(__name__)

def map_columns(df: pd.DataFrame, mapping: Dict[str, str], required_columns: Iterable[str]) -> pd.DataFrame:
    """
    One-to-one mapping: destination_col -> source_col.
    Pads missing destination columns with None.
    """
    try:
        logger.info("Starting column mapping | input_cols=%s | required_cols=%s",
                    list(df.columns), list(required_columns))

        out = pd.DataFrame()

        for dest_col, src_col in mapping.items():
            if src_col in df.columns:
                out[dest_col] = df[src_col]
            else:
                logger.warning("Source column '%s' not found; filling destination '%s' with None",
                               src_col, dest_col)
                out[dest_col] = None

        # Ensure ordering & padding for required columns
        for col in required_columns:
            if col not in out.columns:
                logger.warning("Required destination column '%s' missing in mapping; padding with None", col)
                out[col] = None

        out = out[[c for c in required_columns]]

        logger.info("Column mapping completed | rows=%d | cols=%d", len(out), len(out.columns))
        return out

    except Exception as e:
        logger.exception("Column mapping failed: %s", e)
        raise
