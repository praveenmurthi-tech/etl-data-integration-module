from __future__ import annotations
import argparse
import logging
from typing import Optional, List
import os

from sqlalchemy import create_engine

from etl.core.config_loader import load_yaml_config, load_env_pg
from etl.core.db import build_source_url, build_pg_url, make_engine
from etl.core.logging import setup_logging
from etl.core import audit as audit_core
from etl.extract.sql_extractor import extract_chunks
from etl.transform.mapper import map_columns
from etl.load.pg_loader import upsert_df

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
    logger = logging.getLogger("etl.cli")
    cfg = load_yaml_config(args.customer_config)
    
    # Engines
    src_url = build_source_url(
        cfg.source.type,
        cfg.source.host,
        cfg.source.port,
        cfg.source.database,
        cfg.source.username,
        cfg.source.password,
        cfg.source.driver,
    )
    
    dst_url = build_pg_url(cfg.destination)    
    src_engine = make_engine(src_url)
    dst_engine = make_engine(dst_url)
    
    # Ensure audit tables exist
    from etl.models.audit_models import Base
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
        total_in = 0
        chunks = extract_chunks(src_engine, dataset_cfg.source_table, inc_col, last_value, args.chunksize)
        dfs = []
        for chunk in chunks:
            total_in += len(chunk)
            dfs.append(chunk)
        audit_core.end_step(dst_engine, step_id, "success", total_in, total_in, None)

        # TRANSFORM
        step_id = audit_core.start_step(dst_engine, run_id, "transform")
        total_out = 0
        mapped = []
        for df in dfs:
            out = map_columns(df, dataset_cfg.mapping, req_cols)
            total_out += len(out)
            mapped.append(out)
        import pandas as pd
        final_df = pd.concat(mapped, ignore_index=True) if mapped else pd.DataFrame(columns=req_cols)
        audit_core.end_step(dst_engine, step_id, "success", total_in, total_out, None)

        # LOAD
        step_id = audit_core.start_step(dst_engine, run_id, "load")
        rowcount = upsert_df(dst_engine, final_df, dataset_cfg.target_table, dataset_cfg.key_columns)
        audit_core.end_step(dst_engine, step_id, "success", total_out, rowcount, None)

        # END RUN
        audit_core.end_run(dst_engine, run_id, "success", rowcount, last_value, None)
        logger.info("ETL completed successfully | rows_upserted=%s", rowcount)

    except Exception as e:
        logger.exception("ETL failed: %s", e)
        audit_core.end_run(dst_engine, run_id, "failed", None, None, str(e))
        raise

if __name__ == "__main__":
    main()
