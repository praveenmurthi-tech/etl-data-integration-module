import pandas as pd
from etl.transform.mapper import map_columns

def test_map_columns_padding_and_order():
    df = pd.DataFrame({
        "invoice_id": [1, 2],
        "customer_id": ["A","B"],
        "amount": [10.5, 20.0],
        "currency": ["USD","EUR"],
        "updated_at": ["2024-01-01","2024-01-02"],
    })
    mapping = {
        "invoice_id": "invoice_id",
        "customer_id": "customer_id",
        "amount": "amount",
        "currency": "currency",
        "updated_at": "updated_at",
    }
    required = ["invoice_id","customer_id","amount","currency","updated_at"]
    out = map_columns(df, mapping, required)
    assert list(out.columns) == required
    assert len(out) == 2
