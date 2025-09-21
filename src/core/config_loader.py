from __future__ import annotations
from typing import Any, Dict, Optional
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, PrivateAttr
from dataclasses import dataclass
import os

class IncrementalConfig(BaseModel):
    column: Optional[str] = None
    start_from: Optional[str] = None  # str to keep simple (timestamp or number as string)

class DatasetConfig(BaseModel):
    source_table: str
    target_table: str
    key_columns: list[str]
    mapping: dict[str, str]  # destination_col: source_col (one-to-one)
    incremental: Optional[IncrementalConfig] = None

class SourceConfig(BaseModel):
    type: str  # file | mssql | mysql | postgresql | mongodb

    # Common DB fields (used only if type is mssql/mysql/postgresql)
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    driver: Optional[str] = None  # for MSSQL ODBC driver

    # File-specific
    path: Optional[str] = None
    format: Optional[str] = None

    # MongoDB-specific
    uri: Optional[str] = None
    collection: Optional[str] = None


class DestConfig(BaseModel):
    host: str
    port: int
    database: str
    username: str
    password: str

class CustomerConfig(BaseModel):
    customer: str
    source: SourceConfig
    destination: Optional[DestConfig] = None
    datasets: dict[str, DatasetConfig]
    _file_path: Optional[Path] = None


def load_yaml_config(path: str | Path) -> CustomerConfig:
    path = Path(path).resolve()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    cfg = CustomerConfig.model_validate(data)
    cfg._file_path = path
    return cfg


# Optional env-driven PG destination (fallback if not in YAML)
class EnvPg(BaseModel):
    host: str = Field(default_factory=lambda: os.getenv("PG_HOST", "localhost"))
    port: int = Field(default_factory=lambda: int(os.getenv("PG_PORT", "5432")))
    database: str = Field(default_factory=lambda: os.getenv("PG_DB", "postgres"))
    username: str = Field(default_factory=lambda: os.getenv("PG_USER", "postgres"))
    password: str = Field(default_factory=lambda: os.getenv("PG_PASSWORD", "postgres"))

def load_env_pg() -> EnvPg:
    return EnvPg()
