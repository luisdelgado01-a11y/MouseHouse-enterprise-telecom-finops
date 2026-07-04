"""
CHARGEBACK / SHOWBACK model.

Allocates total telecom service-area cost to the business units that consume each
service, using a documented consumption-weight matrix (the ServiceNow pattern of
mapping IT/telecom cost to business services and cost centers). Produces a per-BU
showback statement and a stacked allocation chart for leadership.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC, ASSETS = ROOT/"data"/"processed", ROOT/"assets"
rng = np.random.default_rng(7)
NAVY = "#1F3864"

sam = pd.read_csv(PROC/"fct_service_area_monthly.csv")
# total cost by service area = telecom spend + incident cost
cost = (sam.groupby("service_area")[["telecom_spend","incident_cost"]].sum().sum(axis=1))

BUSINESS_UNITS = ["Parks & Resorts", "Entertainment", "Consumer Products",
                  "Corporate/Shared", "Media Networks"]

# Documented consumption-weight matrix (rows=service area, cols=BU); each row sums to 1
areas = cost.index.tolist()
W = rng.dirichlet(np.ones(len(BUSINESS_UNITS)), size=len(areas))
weights = pd.DataFrame(W, index=areas, columns=BUSINESS_UNITS).round(3)
weights.to_csv(ROOT/"docs"/"chargeback_weights.csv")

# Allocate
alloc = weights.mul(cost, axis=0)                 # $ by area x BU
showback = alloc.sum(axis=0).sort_values(ascending=False)   # $ per BU
statement = alloc.T
statement["TOTAL"] = statement.sum(axis=1)
statement.round(0).to_csv(PROC/"fct_chargeback.csv")

print("Showback by business unit:")
for bu, amt in showback.items():
    print(f"  {bu:<20} ${amt:,.0f}  ({amt/showback.sum():.1%})")
print(f"  {'TOTAL':<20} ${showback.sum():,.0f}")

# Stacked chart: cost by service area, colored by BU
ax = alloc.plot(kind="bar", stacked=True, figsize=(9.5,5), colormap="viridis")
ax.set_title("Telecom Cost Allocation (Showback) by Service Area to Business Unit",
             color=NAVY, fontweight="bold")
ax.set_ylabel("Allocated cost ($)"); ax.set_xlabel("")
ax.legend(fontsize=7, title="Business Unit")
plt.xticks(rotation=25, ha="right", fontsize=8)
plt.tight_layout(); plt.savefig(ASSETS/"chargeback_showback.png", dpi=120); plt.close()

with open(ROOT/"reports"/"chargeback_summary.md","w") as f:
    f.write("# Chargeback / Showback (auto-generated)\n\n")
    f.write("Allocation of total telecom + incident cost to business units by consumption weight.\n\n")
    f.write("| Business Unit | Allocated Cost | Share |\n|---|--:|--:|\n")
    for bu, amt in showback.items():
        f.write(f"| {bu} | ${amt:,.0f} | {amt/showback.sum():.1%} |\n")
    f.write(f"| **TOTAL** | **${showback.sum():,.0f}** | 100% |\n")
print("chargeback outputs written")
