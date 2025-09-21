from __future__ import annotations
import argparse
import logging
from typing import Optional, List
import os

from sqlalchemy import create_engine

from src.core.config_loader import load_yaml_config, load_env_pg
from src.core.db import build_source_url, build_pg_url, make_engine
from src.core.logging import setup_logging
from src.core import audit as audit_core
from src.extract.extractor import extract_chunks, extract_file_chunks, extract_mongo
from src.config import DEST_DB, DEST_HOST, DEST_PASS, DEST_PORT, DEST_USER
import polars as pl


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


def required_columns_for(dataset: str) -> List[str]:
    if dataset == "sales":
        return REQUIRED_SALES
    if dataset == "services":
        return REQUIRED_SERVICES
    raise ValueError(f"Unknown dataset: {dataset}")

def main():
    parser = argparse.ArgumentParser(description="Run ETL for a dataset and customer config.")
    parser.add_argument("--customer-config", required=True, help="Path to YAML config file")
    parser.add_argument("--dataset", required=True, choices=["sales", "services"], help="Dataset name")    
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"), help="Log level (INFO/DEBUG)")
    parser.add_argument("--chunksize", type=int, default=50000, help="Rows per chunk for extraction")    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    logger = logging.getLogger("src.cli")
    cfg = load_yaml_config(args.customer_config)
    customer_name = cfg.customer
    
    # Engines
    src_url = build_source_url(
        cfg.source.type,
        cfg.source.host,
        cfg.source.port,
        cfg.source.database,
        cfg.source.username,
        cfg.source.password,
        cfg.source.driver
    )

    dest = {
        "host": os.getenv("DEST_HOST"),
        "port": os.getenv("DEST_PORT"),
        "database": os.getenv("DEST_DB"),
        "username": os.getenv("DEST_USER"),
        "password": os.getenv("DEST_PASS"),
    }

    dst_url = build_pg_url(dest)
    src_engine = make_engine(src_url)
    dst_engine = make_engine(dst_url)
    
    # Ensure audit tables exist
    from src.models.audit_models import Base
    Base.metadata.create_all(dst_engine)

    dataset_cfg = cfg.datasets[args.dataset]
    req_cols = required_columns_for(args.dataset)
    
    logger.info("Starting ETL | customer=%s dataset=%s", cfg.customer, args.dataset)
    run_id = audit_core.start_run(dst_engine, cfg.customer, args.dataset)
    
    try:
        inc_col = dataset_cfg.incremental.column if dataset_cfg.incremental else None
        last_value = None  # Could be read from previous run in etl_run (left simple for now)

        # EXTRACT
        step_id = audit_core.start_step(dst_engine, run_id, "extract")
        file_count = 0
        
        config_name = os.path.basename(args.customer_config)
        

        if cfg.source.type in ("mysql", "mssql", "postgresql"):
            files = extract_chunks(src_engine, dataset_cfg.source_table,
                                   customer_name, args.dataset, run_id,
                                   dst_engine, out_dir="data_lake",
                                   incremental_column=inc_col,
                                   last_value=last_value,
                                   chunksize=args.chunksize, data_type=args.dataset,config_name=config_name)
        elif cfg.source.type == "file":
            files = extract_file_chunks(cfg.source.path, cfg.source.format,
                                        customer_name, args.dataset, run_id,
                                        dst_engine, out_dir="data_lake",
                                        chunksize=args.chunksize, data_type=args.dataset,config_name=config_name)
        elif cfg.source.type == "mongodb":
            files = extract_mongo(cfg.source, customer_name, args.dataset,
                                  run_id, dst_engine, out_dir="data_lake",
                                  chunksize=args.chunksize, data_type=args.dataset,config_name=config_name)
        else:
            raise ValueError(f"Unsupported source type: {cfg.source.type}")

        for file_path in files:
            logger.info("Stored extracted file: %s", file_path)
            file_count += 1

        audit_core.end_step(
            dst_engine,
            step_id,
            status="success",
            input_rows=None,
            output_rows=file_count,
            notes=f"{file_count} files extracted"
        )

        # Mark run as successful
        audit_core.end_run(
            dst_engine,
            run_id,
            status="success",
            row_count=None,       # total rows optional; you could sum from file logs
            last_value=last_value,
            error_message=None
        )

        logger.info("ETL completed successfully | run_id=%s", run_id)

    except Exception as e:
        logger.exception("ETL failed for run_id=%s", run_id)

        # Fail step (if started)
        try:
            audit_core.end_step(
                dst_engine,
                step_id,
                status="failed",
                input_rows=None,
                output_rows=None,
                notes=str(e)
            )
        except Exception:
            logger.warning("Failed to log end_step due to earlier error.")

        # Fail run
        audit_core.end_run(
            dst_engine,
            run_id,
            status="failed",
            row_count=None,
            last_value=None,
            error_message=str(e)
        )

        raise  # re-raise so caller sees the failure

if __name__ == "__main__":
    main()