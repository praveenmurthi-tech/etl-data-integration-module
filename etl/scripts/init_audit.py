from sqlalchemy import create_engine
from etl.core.db import build_pg_url
from etl.core.config_loader import load_env_pg
from etl.models.audit_models import Base

def main():
    env_pg = load_env_pg()
    url = build_pg_url(env_pg)
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    print("Audit tables created/verified.")

if __name__ == "__main__":
    main()
