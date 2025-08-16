from __future__ import annotations
from typing import Literal, Optional
from sqlalchemy.engine import URL
from sqlalchemy import create_engine

def build_source_url(
    type_: Literal["mssql", "mysql", "postgresql"],
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    driver: Optional[str] = None,
) -> str:
    try:
        if type_ == "postgresql":
            return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"

        elif type_ == "mysql":
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"

        elif type_ == "mssql":
            # Using pyodbc; driver must be provided (e.g., 'ODBC Driver 17 for SQL Server')
            if not driver:
                raise ValueError("❌ MSSQL requires an ODBC driver name in config.source.driver")
            return f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver={driver}"

        else:
            raise ValueError(f"❌ Unsupported source type: {type_}")

    except Exception as e:
        # Clear logging of the issue
        print("\n[ERROR] Failed to build database connection URL:")
        if type_ == "mssql":
            print(f"  ➤ Driver    : {driver}")
        print(f"  ➤ Reason    : {str(e)}\n")
        raise   # re-raise so calling code can also handle it


def build_pg_url(dest) -> str:
    return f"postgresql+psycopg2://{dest.username}:{dest.password}@{dest.host}:{dest.port}/{dest.database}"

def make_engine(url: str):
    return create_engine(url, future=True)
