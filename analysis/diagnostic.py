"""
DIAGNOSTIC analysis: cost driver waterfall (bridge).

Answers the executive question "why is our telecom cost what it is?" by bridging
from a clean contracted baseline to actual total cost, decomposed into the specific
drivers the invoice audit found (rate overcharges, duplicate charges, ghost
circuits) plus incident-resolution cost. This is the finance "bridge" that turns a
number into a story.
"""
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC, ASSETS, RAW = ROOT/"data"/"processed", ROOT/"assets", ROOT/"data"/"raw"
NAVY, RED, TEAL, GRN = "#1F3864", "#C0392B", "#2E86AB", "#27AE60"

audit = pd.read_csv(PROC/"fct_invoice_audit.csv")
inc   = pd.read_csv(RAW/"servicenow_incidents.csv")

# Contracted baseline = sum of contracted rates on legitimately billed lines
baseline = audit.loc[audit.finding != "Ghost circuit", "contracted_rate"].sum()

# Driver effects from the audit
over  = audit.loc[audit.finding == "Rate overcharge", "variance"].clip(lower=0).sum()
dup   = audit.loc[audit.finding == "Duplicate charge", "variance"].clip(lower=0).sum()
ghost = audit.loc[audit.finding == "Ghost circuit", "billed_amount"].sum()
incident_cost = inc["cost_to_resolve"].sum()
total = baseline + over + dup + ghost + incident_cost

steps = [("Contracted\nbaseline", baseline, NAVY),
         ("Rate\novercharges", over, RED),
         ("Duplicate\ncharges", dup, RED),
         ("Ghost\ncircuits", ghost, RED),
         ("Incident\nresolution", incident_cost, TEAL),
         ("Actual\ntotal cost", total, GRN)]

fig, ax = plt.subplots(figsize=(9.5, 5))
running = 0
for i, (label, val, color) in enumerate(steps):
    if label.startswith("Contracted") or label.startswith("Actual"):
        ax.bar(i, val, color=color)
        ax.text(i, val, f"${val/1e6:.2f}M", ha="center", va="bottom", fontsize=9, fontweight="bold")
        running = val
    else:
        ax.bar(i, val, bottom=running, color=color)
        ax.text(i, running + val, f"+${val/1e3:,.0f}K", ha="center", va="bottom", fontsize=8)
        running += val
ax.set_xticks(range(len(steps)))
ax.set_xticklabels([s[0] for s in steps], fontsize=8)
ax.set_title("Telecom Cost Driver Bridge: Contracted Baseline to Actual Total Cost",
             color=NAVY, fontweight="bold")
ax.set_ylabel("Cost ($)")
plt.tight_layout(); plt.savefig(ASSETS/"cost_driver_bridge.png", dpi=120); plt.close()

controllable = over + dup + ghost
print(f"Contracted baseline:      ${baseline:,.0f}")
print(f"+ Rate overcharges:       ${over:,.0f}")
print(f"+ Duplicate charges:      ${dup:,.0f}")
print(f"+ Ghost circuits:         ${ghost:,.0f}")
print(f"+ Incident resolution:    ${incident_cost:,.0f}")
print(f"= Actual total cost:      ${total:,.0f}")
print(f"Controllable overbilling (recoverable): ${controllable:,.0f} ({controllable/total:.1%} of total)")

with open(ROOT/"reports"/"diagnostic_summary.md","w") as f:
    f.write("# Diagnostic: Cost Driver Bridge (auto-generated)\n\n")
    f.write(f"- Contracted baseline: **${baseline:,.0f}**\n")
    f.write(f"- Rate overcharges: **+${over:,.0f}**\n")
    f.write(f"- Duplicate charges: **+${dup:,.0f}**\n")
    f.write(f"- Ghost circuits: **+${ghost:,.0f}**\n")
    f.write(f"- Incident resolution: **+${incident_cost:,.0f}**\n")
    f.write(f"- **Controllable overbilling: ${controllable:,.0f}** ({controllable/total:.1%} of total)\n")
