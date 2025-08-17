# Config-Driven ETL (Sales & Services) – Python

A professional, plain-Python repository scaffold for config-driven ETL to extract from various SQL sources (MSSQL/PostgreSQL), 
transform via **one-to-one mappings** defined in YAML, and load into **PostgreSQL**, with **file + DB audit logging**.

## Features
- **YAML-first** configuration (per-customer).
- **Multi-source** via SQLAlchemy (mysql/postgresql).
- **Chunked extraction** and optional **incremental filter** (timestamp or numeric increment).
- **One-to-one mapping** transformer with schema padding.
- **Upsert to PostgreSQL** using `ON CONFLICT` with configurable key(s).
- **Audit** tables tracked in PostgreSQL (runs + steps) and file logs (rotating).

## Quickstart

1. **Python**: 3.9+ recommended.
2. Install dependencies (dev tools optional):
   ```bash
   pip install -e .
   # or
   pip install -r requirements.txt
   ```

3. Set environment (optional – otherwise config must contain credentials):
   Create a `.env` file (see `.env.example`).

4. Initialize audit tables (first time only):
   ```bash
   python -m etl.scripts.init_audit
   ```

5. **Run a dataset** (sales or services) for a customer:
   ```bash
   python -m etl.cli --customer-config etl/config/customers/sample_customer.yaml --dataset sales
   python -m etl.cli --customer-config etl/config/customers/sample_customer.yaml --dataset services
   ```

## Config (YAML)

See: `etl/config/customers/sample_customer.yaml`

Key sections:
- `source`: connection + type (`mssql` | `postgresql`).
- `destination`: PostgreSQL connection.
- `datasets.<name>`: source table, target table, key columns (for upsert), optional incremental, and **one-to-one** `mapping`.

## Incremental
If `datasets.<name>.incremental.column` is present, the extractor applies a `WHERE` clause of the form:
- `column > last_value` (numeric) or `column > last_value` (timestamp).
The last processed value is stored in the audit run row. If unset, a full load is executed.

## Linting/Formatting/Typing/Tests
- Ruff, Black, Mypy, Pytest are configured via `pyproject.toml`.
```bash
ruff check .
black .
mypy etl
pytest -q
```

## Notes
- Ensure appropriate DB drivers are installed for your sources:
  - MSSQL: `pyodbc` or `pymssql` (URI: `mssql+pyodbc://...`).
  - PostgreSQL: `psycopg2-binary` (URI: `postgresql+psycopg2://...`).

