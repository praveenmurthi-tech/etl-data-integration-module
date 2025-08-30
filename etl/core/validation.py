from __future__ import annotations
from typing import Tuple, Dict, Any
import pandas as pd
import logging
from datetime import datetime
from decimal import Decimal
import uuid

logger = logging.getLogger(__name__)


class DataValidator:
    """Validate and coerce DataFrames based on predefined table schemas."""

    # Hardcoded schemas for destination tables
    SCHEMAS: Dict[str, Dict[str, str]] = {
        "sales": {
            "sale_id": "uuid",
            "customer_id": "uuid",
            "product_id": "uuid",
            "sale_date": "date",
            "sale_amount": "decimal",
            "sale_currency": "string",
            "quantity_sold": "int",
            "salesperson_name": "string",
            "region": "string",
            "payment_mode": "string",
            "tax_amount": "decimal",
            "discount_amount": "decimal",
            "net_amount": "decimal",
            "created_at": "datetime",
            "updated_at": "datetime",
        },
        "services": {
            "service_id": "uuid",
            "customer_id": "uuid",
            "service_date": "date",
            "service_type": "string",
            "service_amount": "decimal",
            "service_currency": "string",
            "technician_name": "string",
            "service_status": "string",
            "service_duration": "int",
            "parts_used": "string",
            "warranty_applied": "bool",
            "follow_up_required": "bool",
            "remarks": "string",
            "created_at": "datetime",
            "updated_at": "datetime",
        }
    }

    def __init__(self, table_name: str):
        if table_name not in self.SCHEMAS:
            raise ValueError(f"Unknown table schema: {table_name}")
        self.table_name = table_name
        self.schema = self.SCHEMAS[table_name]

    def validate_and_fix(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Validate and coerce dataframe rows.
        Returns (valid_df, invalid_df)."""

        valid_rows = []
        invalid_rows = []

        for idx, row in df.iterrows():
            try:
                fixed_row = self._coerce_row(row.to_dict())
                valid_rows.append(fixed_row)
            except Exception as e:
                logger.warning("Row %s failed validation: %s", idx, e)
                bad_row = row.to_dict()
                bad_row["_error"] = str(e)
                invalid_rows.append(bad_row)

        return pd.DataFrame(valid_rows), pd.DataFrame(invalid_rows)

    def _coerce_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        fixed = {}
        for col, col_type in self.schema.items():
            val = row.get(col)

            if val is None or (isinstance(val, float) and pd.isna(val)):
                fixed[col] = None
                continue

            try:
                if col_type == "uuid":
                    fixed[col] = str(uuid.UUID(str(val)))
                elif col_type == "int":
                    fixed[col] = int(val)
                elif col_type == "decimal":
                    fixed[col] = Decimal(str(val))
                elif col_type == "string":
                    fixed[col] = str(val)
                elif col_type == "date":
                    fixed[col] = pd.to_datetime(val).date()
                elif col_type == "datetime":
                    fixed[col] = pd.to_datetime(val)
                elif col_type == "bool":
                    fixed[col] = bool(val)
                else:
                    fixed[col] = val
            except Exception as e:
                raise ValueError(f"Column '{col}' invalid value '{val}': {e}")

        return fixed
