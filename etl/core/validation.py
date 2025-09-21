from __future__ import annotations
from typing import Tuple, Dict, Any
import polars as pl
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class DataValidator:
    """Validate and coerce Polars DataFrames based on predefined table schemas."""

    SCHEMAS: Dict[str, Dict[str, Any]] = {
        "sales": {
            "sale_id": pl.Utf8,
            "customer_id": pl.Utf8,
            "product_id": pl.Utf8,
            "sale_date": pl.Date,
            "sale_amount": pl.Float64,
            "sale_currency": pl.Utf8,
            "quantity_sold": pl.Int64,
            "salesperson_name": pl.Utf8,
            "region": pl.Utf8,
            "payment_mode": pl.Utf8,
            "tax_amount": pl.Float64,
            "discount_amount": pl.Float64,
            "net_amount": pl.Float64,
            "created_at": pl.Datetime("us"),
            "updated_at": pl.Datetime("us"),
        },
        "services": {
            "service_id": pl.Utf8,
            "customer_id": pl.Utf8,
            "service_date": pl.Date,
            "service_type": pl.Utf8,
            "service_amount": pl.Float64,
            "service_currency": pl.Utf8,
            "technician_name": pl.Utf8,
            "service_status": pl.Utf8,
            "service_duration": pl.Int64,
            "parts_used": pl.Utf8,
            "warranty_applied": pl.Boolean,
            "follow_up_required": pl.Boolean,
            "remarks": pl.Utf8,
            "created_at": pl.Datetime("us"),
            "updated_at": pl.Datetime("us"),
        },
    }

    REQUIRED_FIELDS: Dict[str, list[str]] = {
        "sales": ["sale_date", "sale_amount", "tax_amount", "net_amount", "quantity_sold", "product_id"],
        "services": ["service_date", "service_amount", "service_type"]
    }

    def __init__(self, table_name: str):
        if table_name not in self.SCHEMAS:
            raise ValueError(f"Unknown table schema: {table_name}")
        self.table_name = table_name
        self.schema = self.SCHEMAS[table_name]
        self.required_fields = (self.REQUIRED_FIELDS.
                                get(table_name, []))

    def validate_and_fix(self, df: pl.DataFrame) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """Validate and coerce Polars DataFrame rows. Returns (valid_df, invalid_df).
        If mandatory columns are missing → raise ValueError (file-level failure).
        """

        # === Check if required columns are present in the file ===
        missing_cols = [col for col in self.required_fields if col not in df.columns]
        if missing_cols:
            msg = f"Validation failed: Required columns missing → {missing_cols}"
            logger.error(msg)
            raise ValueError(msg)   # stop file processing immediately

        valid_rows = []
        invalid_rows = []

        for row in df.to_dicts():
            try:
                fixed_row = self._coerce_row(row)

                # check for empty mandatory fields
                for field in self.required_fields:
                    if fixed_row.get(field) in (None, "", "nan"):
                        raise ValueError(f"Missing mandatory field: {field}")

                valid_rows.append(fixed_row)

            except Exception as e:
                row["_error"] = str(e)
                invalid_rows.append(row)

        valid_df = pl.DataFrame(valid_rows, schema=self.schema) if valid_rows else pl.DataFrame(schema=self.schema)
        invalid_schema = {**self.schema, "_error": pl.Utf8}
        invalid_df = pl.DataFrame(invalid_rows, schema=invalid_schema) if invalid_rows else pl.DataFrame(schema=invalid_schema)

        return valid_df, invalid_df

    def _coerce_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        fixed = {}
        for col, col_type in self.schema.items():
            val = row.get(col)

            if val is None:
                fixed[col] = None
                continue

            try:
                if col.endswith("_id"):
                    val_str = str(val)
                    if len(val_str) in (32, 36):
                        fixed[col] = str(uuid.UUID(val_str))
                    else:
                        fixed[col] = val_str
                elif col_type == pl.Int64:
                    fixed[col] = int(val)
                elif col_type == pl.Float64:
                    fixed[col] = float(val)
                elif col_type == pl.Utf8:
                    fixed[col] = str(val)
                elif col_type == pl.Date:
                    fixed[col] = datetime.fromisoformat(str(val)).date()
                elif isinstance(col_type, pl.Datetime):
                    fixed[col] = datetime.fromisoformat(str(val))
                elif col_type == pl.Boolean:
                    fixed[col] = bool(val)
                else:
                    fixed[col] = val
            except Exception as e:
                raise ValueError(f"Column '{col}' invalid value '{val}': {e}")

        return fixed
