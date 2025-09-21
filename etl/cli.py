from __future__ import annotations
import argparse
import logging
import os
import polars as pl
from pathlib import Path
from sqlalchemy.orm import Session

from etl.core.db import build_pg_url, make_engine
from etl.core.logging import setup_logging
from etl.models.audit_models import FileExtractionLog
from etl.core.config_loader import load_yaml_config
from etl.transform.mapper import map_columns
from etl.core.validation import DataValidator
from etl.load.pg_loader import upsert_df
import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError


sqlalchemy.exc._include_sql_text = False


REQUIRED_SALES = [
    "sale_id", "customer_id", "product_id", "sale_date",
    "sale_amount", "sale_currency", "quantity_sold",
    "salesperson_name", "region", "payment_mode",
    "tax_amount", "discount_amount", "net_amount",
    "created_at", "updated_at"
]

REQUIRED_SERVICES = [
    "service_id", "customer_id", "service_date", "service_type",
    "service_amount", "service_currency", "technician_name",
    "service_status", "service_duration", "parts_used",
    "warranty_applied", "follow_up_required", "remarks",
    "created_at", "updated_at"
]


def required_columns_for(dataset: str) -> list[str]:
    if dataset == "sales":
        return REQUIRED_SALES
    if dataset == "services":
        return REQUIRED_SERVICES
    raise ValueError(f"Unknown dataset: {dataset}")


def main():
    parser = argparse.ArgumentParser(description="Run ETL ingestion for pending files.")
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"),
                        help="Log level (INFO/DEBUG)")
    args = parser.parse_args()

    setup_logging(args.log_level)
    logger = logging.getLogger("etl.ingest")

    # === Destination DB ===
    dest = {
        "host": os.getenv("DEST_HOST"),
        "port": os.getenv("DEST_PORT"),
        "database": os.getenv("DEST_DB"),
        "username": os.getenv("DEST_USER"),
        "password": os.getenv("DEST_PASS"),
    }
    dst_url = build_pg_url(dest)
    dst_engine = make_engine(dst_url)

    # === Pick pending files (any dataset/type) ===
    with Session(dst_engine) as sess:
        pending_files = (
            sess.query(FileExtractionLog)
            .filter(FileExtractionLog.ingestion_status == "pending")
            .order_by(FileExtractionLog.id.asc())
            .all()
        )

    if not pending_files:
        logger.info("No pending files for ingestion.")
        return

    logger.info("Found %d pending files to process", len(pending_files))

    for file_log in pending_files:
        dataset = file_log.data_type       # sales / services
        config_name = file_log.config_name # YAML file name

        # === Load config ===
        cfg = load_yaml_config(f"etl/config/customers/{config_name}")
        dataset_cfg = cfg.datasets[dataset]
        req_cols = required_columns_for(dataset)

        file_path = Path(file_log.file_path)
        if not file_path.is_absolute():
            base_dir = Path("D:/etl_extractor")
            final_path = base_dir / file_path
        else:
            final_path = file_path

        try:
            logger.info("Processing file: %s (rows=%d)", final_path, file_log.rows)

            # === EXTRACT FILE ===
            df = pl.read_parquet(str(final_path))

            # === TRANSFORM ===
            mapped_df = map_columns(df, dataset_cfg.mapping, req_cols, cfg.customer)

            # === VALIDATE ===
            validator = DataValidator(dataset)

            try:
                valid_df, invalid_df = validator.validate_and_fix(mapped_df)
            except ValueError as ve:
                # file-level failure (e.g. missing mandatory columns)
                logger.error("❌ Validation error for file %s: %s", final_path, ve)
                with Session(dst_engine) as sess:
                    db_file = sess.get(FileExtractionLog, file_log.id)
                    db_file.ingestion_status = "failed"
                    db_file.error_message = str(ve)
                    sess.commit()
                continue  # skip this file

            # If invalid rows exist → stringify them before saving
            if not invalid_df.is_empty():
                bad_path = str(final_path).replace(".parquet", "_invalid.csv")
                # force all invalid values to string (safe for CSV)
                invalid_str_rows = [
                    {k: ("" if v is None else str(v)) for k, v in row.items()}
                    for row in invalid_df.to_dicts()
                ]
                invalid_df = pl.DataFrame(invalid_str_rows)
                invalid_df.write_csv(bad_path)

                msg = f"Validation failed for {len(invalid_df)} rows in {final_path}. Written to {bad_path}"
                logger.error("❌ %s", msg)
                with Session(dst_engine) as sess:
                    db_file = sess.get(FileExtractionLog, file_log.id)
                    db_file.ingestion_status = "failed"
                    db_file.error_message = msg
                    sess.commit()
                continue  # stop further processing of this file

            # === LOAD ===
            target_table = dataset_cfg.target_table
            key_columns = dataset_cfg.key_columns

            rowcount = upsert_df(dst_engine, valid_df, target_table, key_columns)
            logger.info("✅ Upserted %d rows from file %s", rowcount, final_path)

            # === Update status → success ===
            with Session(dst_engine) as sess:
                db_file = sess.get(FileExtractionLog, file_log.id)
                db_file.ingestion_status = "success"
                db_file.error_message = None
                sess.commit()

        except Exception as e:
            logger.exception("Failed processing file %s: %s", final_path, e)
            with Session(dst_engine) as sess:
                db_file = sess.get(FileExtractionLog, file_log.id)
                db_file.ingestion_status = "failed"
                db_file.error_message = str(e)
                sess.commit()


if __name__ == "__main__":
    main()
