from etl.core.config_loader import load_yaml_config
from pathlib import Path

def test_load_yaml_config():
    cfg = load_yaml_config(Path(__file__).parents[1] / "etl/config/customers/sample_customer.yaml")
    assert cfg.customer == "acme_corp"
    assert "sales" in cfg.datasets
    assert cfg.source.type in {"postgresql","mysql","mssql"}
