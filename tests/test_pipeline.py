"""Data-quality + logic tests (run in CI)."""
import pandas as pd, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def _proc(name): return pd.read_csv(ROOT/"data"/"processed"/f"{name}.csv")

def test_marts_exist():
    for t in ["fct_invoice_audit","fct_service_area_monthly","fct_budget_variance","fct_vendor_scorecard"]:
        assert (ROOT/"data"/"processed"/f"{t}.csv").exists(), f"missing {t}"

def test_no_negative_spend():
    sam = _proc("fct_service_area_monthly")
    assert (sam.telecom_spend >= 0).all()

def test_audit_flags_present():
    audit = _proc("fct_invoice_audit")
    assert audit.finding.isin(["OK","Rate overcharge","Duplicate charge","Ghost circuit"]).all()
    assert (audit.finding != "OK").sum() > 0, "audit should catch planted billing errors"

def test_budget_variance_balances():
    bv = _proc("fct_budget_variance")
    assert abs((bv.actual_spend - bv.annual_budget - bv.variance).sum()) < 1e-6

def test_chargeback_allocates_full_cost():
    cb = pd.read_csv(ROOT/"data"/"processed"/"fct_chargeback.csv", index_col=0)
    # each service area row (excluding TOTAL column) allocates to BUs; totals must be positive
    assert cb["TOTAL"].sum() > 0
    # allocation total should match sum of per-BU columns
    bu_cols = [c for c in cb.columns if c != "TOTAL"]
    total, parts = cb["TOTAL"].sum(), cb[bu_cols].sum().sum()
    assert abs(parts - total) / total < 1e-3   # rounding tolerance

def test_ai_triage_accuracy():
    import sys; sys.path.insert(0, str(ROOT/"src"))
    from ai_triage.triage import evaluate
    _, report, acc = evaluate()
    assert acc > 0.90, f"triage accuracy too low: {acc:.2%}"
    # overcharge + duplicate detection should be strong (the defensible classes)
    strong = report.set_index("label").loc[["rate_overcharge","duplicate"], "f1"]
    assert (strong > 0.8).all()
