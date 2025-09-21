from __future__ import annotations
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class EtlRun(Base):
    __tablename__ = "etl_run"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer = Column(String(255), nullable=False)
    dataset = Column(String(255), nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="running")  # running|success|failed
    row_count = Column(Integer, nullable=True)
    last_incremental_value = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)

class EtlRunStep(Base):
    __tablename__ = "etl_run_step"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, nullable=False)
    step_name = Column(String(255), nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False, default="running")
    input_rows = Column(Integer, nullable=True)
    output_rows = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
class FileExtractionLog(Base):
    __tablename__ = "file_extraction_log"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("etl_run.id"), nullable=False)
    dataset = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    chunk_no = Column(Integer, nullable=False)
    rows = Column(Integer, nullable=False)
    data_type = Column(String, nullable=False)   # sales/services
    config_name = Column(String, nullable=False) # e.g. "customer_a.yaml"
    status = Column(String, default="success")   # extraction status (success/failed)
    ingestion_status = Column(String, default="pending")  # ingestion status (pending/success/failed)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    remark = Column(String, nullable=True)

