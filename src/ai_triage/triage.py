"""
AI-assisted invoice-anomaly TRIAGE + EVAL HARNESS.

Two parts, mirroring frontier AI-evaluation practice:

1) triage_invoice(): for a flagged invoice line, classify the anomaly and generate a
   plain-English "why + recommended action" note for the analyst. `generate_note` is
   template-based so the repo runs offline in CI, but is structured to be swapped for
   a real LLM call (see LLM_PROMPT) with no change to the eval harness.

2) evaluate(): grades the triage's classifications against ground-truth labels
   (precision / recall / F1 / accuracy), the same answer-integrity discipline used
   to grade AI agents. Prevents shipping a model that "sounds right" but is wrong.
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT/"data"/"processed"

LLM_PROMPT = (
    "You are a telecom-expense analyst. Given an invoice line (contracted_rate, "
    "billed_amount, ci_status), classify the anomaly as one of "
    "[rate_overcharge, duplicate, ghost_circuit, none] and explain in one sentence "
    "why, plus the recommended recovery action. Return JSON {label, note}."
)

def classify(row) -> str:
    """Deterministic triage policy (stand-in for an LLM classifier)."""
    if row.ci_status == "Decommissioned":
        return "ghost_circuit"
    if row.billed_amount >= row.contracted_rate * 1.9:
        return "duplicate"
    if row.billed_amount > row.contracted_rate * 1.10:
        return "rate_overcharge"
    return "none"

def generate_note(row, label) -> str:
    over = row.billed_amount - row.contracted_rate
    notes = {
        "ghost_circuit": f"Circuit {row.ci_id} is decommissioned but billed ${row.billed_amount:,.0f}. "
                         f"Action: dispute as a ghost circuit and reclaim ${row.billed_amount:,.0f}.",
        "duplicate":     f"Billed ${row.billed_amount:,.0f} vs contracted ${row.contracted_rate:,.0f} "
                         f"(~2x). Action: flag duplicate charge; recover ${over:,.0f}.",
        "rate_overcharge": f"Billed ${row.billed_amount:,.0f} exceeds contracted ${row.contracted_rate:,.0f} "
                           f"by ${over:,.0f}. Action: request rate correction and credit.",
        "none":          "Within contract terms; no action.",
    }
    return notes[label]

def triage_invoice(row) -> dict:
    label = classify(row)
    return {"invoice_id": row.invoice_id, "predicted": label, "note": generate_note(row, label)}

# ground-truth mapping (audit finding text -> planted_error vocabulary)
GT_MAP = {"OK": "none", "Rate overcharge": "rate_overcharge",
          "Duplicate charge": "duplicate", "Ghost circuit": "ghost_circuit"}

def evaluate():
    audit = pd.read_csv(PROC/"fct_invoice_audit.csv")
    inv = pd.read_csv(ROOT/"data"/"raw"/"telecom_invoices.csv")[["invoice_id","planted_error"]]
    df = audit.merge(inv, on="invoice_id")
    df["truth"] = df["planted_error"].replace({"": "none"}).fillna("none")
    df["predicted"] = df.apply(classify, axis=1)

    labels = ["rate_overcharge","duplicate","ghost_circuit","none"]
    rows, tot_tp = [], 0
    for lab in labels:
        tp = ((df.predicted==lab) & (df.truth==lab)).sum()
        fp = ((df.predicted==lab) & (df.truth!=lab)).sum()
        fn = ((df.predicted!=lab) & (df.truth==lab)).sum()
        prec = tp/(tp+fp) if tp+fp else 0
        rec  = tp/(tp+fn) if tp+fn else 0
        f1   = 2*prec*rec/(prec+rec) if prec+rec else 0
        rows.append((lab, tp, fp, fn, prec, rec, f1)); tot_tp += tp
    acc = (df.predicted==df.truth).mean()
    return df, pd.DataFrame(rows, columns=["label","tp","fp","fn","precision","recall","f1"]), acc

if __name__ == "__main__":
    df, report, acc = evaluate()
    print("AI triage eval: classification vs ground truth")
    print(report.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print(f"\nOverall accuracy: {acc:.1%}")
    # sample generated notes on genuinely flagged lines
    print("\nSample analyst notes:")
    flagged = df[df.predicted != "none"].head(3)
    for _, r in flagged.iterrows():
        print(" -", triage_invoice(r)["note"])
    with open(ROOT/"reports"/"eval_report.md","w") as f:
        f.write("# AI Triage: Eval Report (auto-generated)\n\n")
        f.write(f"Overall classification accuracy vs ground truth: **{acc:.1%}**\n\n")
        f.write("| label | precision | recall | f1 |\n|---|--:|--:|--:|\n")
        for _, r in report.iterrows():
            f.write(f"| {r.label} | {r.precision:.2f} | {r.recall:.2f} | {r.f1:.2f} |\n")
        f.write("\n*Notes are template-generated for offline CI; swap `generate_note` for an LLM call via `LLM_PROMPT`.*\n")
