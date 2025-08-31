from __future__ import annotations
from typing import Literal, Optional
from sqlalchemy import create_engine
import urllib.parse
import logging


logger = logging.getLogger(__name__)  # module-level logger

def build_source_url(
    type_: Literal["mssql", "mysql", "postgresql", "file", "mongodb"],
    host: str = "",
    port: int = 0,
    database: str = "",
    username: str = "",
    password: str = "",
    driver: Optional[str] = None,
    path: Optional[str] = None,
    format: Optional[str] = None,
    uri: Optional[str] = None,
    collection: Optional[str] = None,
) -> Optional[str]:
    """
    Build SQLAlchemy URL for SQL sources.
    For file sources, return None (handled separately).
    """
    try:
        if type_ == "postgresql":
            url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
            logger.info("PostgreSQL URL built successfully | host=%s db=%s", host, database)
            return url

        elif type_ == "mysql":
            username_enc = urllib.parse.quote_plus(username)
            password_enc = urllib.parse.quote_plus(password)
            url = f"mysql+mysqlconnector://{username_enc}:{password_enc}@{host}:{port}/{database}"
            logger.info("MySQL URL built successfully | host=%s db=%s", host, database)
            return url

        elif type_ == "mssql":
            if not driver:
                logger.error("MSSQL requires an ODBC driver name in config.source.driver")
                raise ValueError("MSSQL requires an ODBC driver name in config.source.driver")

            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={host};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password}"
            )
            odbc_params = urllib.parse.quote_plus(conn_str)
            url = f"mssql+pyodbc:///?odbc_connect={odbc_params}"
            logger.info("MSSQL URL built successfully | host=%s db=%s driver=%s", host, database, driver)
            return url

        elif type_ == "file":
            # For files we don't return a DB URL
            logger.info("File source detected: %s (format=%s)", path, format)
            return None


        elif type_ == "mongodb":
            logger.info("MongoDB source detected: uri=%s db=%s collection=%s",
                        uri, database, collection)
            return None

        else:
            logger.error("Unsupported source type: %s", type_)
            raise ValueError(f"Unsupported source type: {type_}")

    except Exception:
        logger.exception("Failed to build connection URL | type=%s host=%s db=%s", type_, host, database)
        raise


def build_pg_url(dest: dict) -> str:
    url = f"postgresql+psycopg2://{dest['username']}:{dest['password']}@{dest['host']}:{dest['port']}/{dest['database']}"
    logger.info("Postgres destination URL built | host=%s db=%s", dest['host'], dest['database'])
    return url



def make_engine(url: str | None):
    if url is None:
        logger.info("Skipping engine creation since source is a file.")
        return None
    try:
        engine = create_engine(url, future=True)
        logger.debug("SQLAlchemy engine created successfully")
        return engine
    except Exception:
        logger.exception("Failed to create SQLAlchemy engine")
        raise