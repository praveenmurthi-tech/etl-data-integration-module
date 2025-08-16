from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from etl.models.audit_models import EtlRun, EtlRunStep, Base
from sqlalchemy.orm import Session

def start_run(engine: Engine, customer: str, dataset: str) -> int:
    with Session(engine) as sess:
        run = EtlRun(customer=customer, dataset=dataset, status="running", started_at=datetime.utcnow())
        sess.add(run)
        sess.commit()
        return run.id

def end_run(engine: Engine, run_id: int, status: str, row_count: Optional[int], last_value: Optional[str], error_message: Optional[str] = None) -> None:
    with Session(engine) as sess:
        run = sess.get(EtlRun, run_id)
        if run:
            run.status = status
            run.row_count = row_count
            run.last_incremental_value = last_value
            run.ended_at = datetime.utcnow()
            run.error_message = error_message
            sess.commit()

def start_step(engine: Engine, run_id: int, step_name: str) -> int:
    with Session(engine) as sess:
        step = EtlRunStep(run_id=run_id, step_name=step_name, status="running", started_at=datetime.utcnow())
        sess.add(step)
        sess.commit()
        return step.id

def end_step(engine: Engine, step_id: int, status: str, input_rows: Optional[int], output_rows: Optional[int], notes: Optional[str] = None) -> None:
    with Session(engine) as sess:
        step = sess.get(EtlRunStep, step_id)
        if step:
            step.status = status
            step.input_rows = input_rows
            step.output_rows = output_rows
            step.ended_at = datetime.utcnow()
            step.notes = notes
            sess.commit()
