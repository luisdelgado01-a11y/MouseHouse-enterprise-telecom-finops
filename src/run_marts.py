"""Load raw CSVs into DuckDB, run the SQL marts, export processed tables."""
import duckdb, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT/"data"/"raw", ROOT/"data"/"processed"
PROC.mkdir(parents=True, exist_ok=True)
con = duckdb.connect()
for csv in RAW.glob("*.csv"):
    con.register(csv.stem, pd.read_csv(csv))
con.execute((ROOT/"models"/"marts.sql").read_text())
for t in ["fct_invoice_audit","fct_service_area_monthly","fct_budget_variance","fct_vendor_scorecard"]:
    con.table(t).to_df().to_csv(PROC/f"{t}.csv", index=False)
    print("built", t)
con.close()
