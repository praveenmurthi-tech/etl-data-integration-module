from __future__ import annotations
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric
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
