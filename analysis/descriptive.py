"""
Descriptive + diagnostic analysis. Produces the headline results the README cites
and saves executive charts to /assets. Runnable: `python analysis/descriptive.py`.
"""
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC, ASSETS = ROOT/"data"/"processed", ROOT/"assets"
ASSETS.mkdir(exist_ok=True)
NAVY, RED, TEAL = "#1F3864", "#C0392B", "#2E86AB"

audit = pd.read_csv(PROC/"fct_invoice_audit.csv")
sam   = pd.read_csv(PROC/"fct_service_area_monthly.csv", parse_dates=["period"])
bv    = pd.read_csv(PROC/"fct_budget_variance.csv")
vend  = pd.read_csv(PROC/"fct_vendor_scorecard.csv")

# --- Headline 1: cost avoidance from invoice audit ---
flagged = audit[audit.finding != "OK"]
recoverable = (flagged.variance.clip(lower=0).sum()
               + audit.loc[audit.finding=="Ghost circuit","billed_amount"].sum())
print(f"Invoice lines audited: {len(audit):,}")
print(f"Flagged lines: {len(flagged):,} ({len(flagged)/len(audit):.1%})")
print(f"Identified recoverable / cost-avoidance: ${recoverable:,.0f}")

# --- Headline 2: service-area deviation (SPC on packet loss vs baseline) ---
# Control limits are set from an early-year baseline (first 3 months); the latest
# period is scored against that baseline so a *drifting* service area is caught early.
sam = sam.sort_values("period")
base = sam[sam.period < sam.period.min() + pd.Timedelta(days=90)]
bstat = base.groupby("service_area")["packet_loss"].agg(["mean","std"])
latest = sam.groupby("service_area").tail(1).set_index("service_area")
pl = bstat.copy()
pl["latest"] = latest["packet_loss"]
pl["z_latest"] = (pl["latest"] - pl["mean"]) / pl["std"]
breaching = pl[pl.z_latest > 3].index.tolist()
print("Service areas breaching control limits (packet loss z>3 vs baseline):", breaching or "none")

# --- Headline 3: costliest vendor ---
vend["rank"] = vend.spend_per_incident.rank(ascending=False)
top_vendor = vend.sort_values("spend_per_incident", ascending=False).iloc[0]
print(f"Highest spend-per-incident vendor: {top_vendor.vendor} (${top_vendor.spend_per_incident:,.0f})")

# --- Chart 1: telecom spend trend by service area ---
piv = sam.pivot_table(index="period", columns="service_area", values="telecom_spend", aggfunc="sum")
ax = piv.plot(figsize=(9,4.5), linewidth=2)
ax.set_title("Monthly Telecom Spend by Service Area", color=NAVY, fontweight="bold")
ax.set_ylabel("Spend ($)"); ax.legend(fontsize=7, ncol=2)
plt.tight_layout(); plt.savefig(ASSETS/"spend_trend.png", dpi=120); plt.close()

# --- Chart 2: budget variance ---
bv2 = bv.sort_values("variance_pct")
colors = [RED if v>0 else TEAL for v in bv2.variance_pct]
ax = bv2.plot.barh(x="service_area", y="variance_pct", color=colors, legend=False, figsize=(8,4))
ax.set_title("Budget Variance by Service Area (Actual vs Coupa Budget)", color=NAVY, fontweight="bold")
ax.set_xlabel("Variance %"); ax.axvline(0, color="black", lw=0.8)
plt.tight_layout(); plt.savefig(ASSETS/"budget_variance.png", dpi=120); plt.close()

# --- Chart 3: packet-loss SPC for the degrading area ---
worst = pl.z_latest.idxmax()
d = sam[sam.service_area==worst].sort_values("period")
m, sd = pl.loc[worst,"mean"], pl.loc[worst,"std"]
ax = d.plot(x="period", y="packet_loss", marker="o", color=NAVY, legend=False, figsize=(9,4))
ax.axhline(m, color="gray", ls="--", lw=1, label="mean")
ax.axhline(m+3*sd, color=RED, ls="--", lw=1, label="upper control limit (3σ)")
ax.set_title(f"Packet Loss Control Chart for {worst} (deviation detected)", color=NAVY, fontweight="bold")
ax.set_ylabel("Packet loss %"); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(ASSETS/"spc_packet_loss.png", dpi=120); plt.close()

# --- Save a results summary the README/report can read ---
(ROOT/"reports").mkdir(exist_ok=True)
with open(ROOT/"reports"/"results_summary.md","w") as f:
    f.write("# Results Summary (auto-generated)\n\n")
    f.write(f"- Invoice lines audited: **{len(audit):,}**\n")
    f.write(f"- Flagged mis-billed lines: **{len(flagged):,}** ({len(flagged)/len(audit):.1%})\n")
    f.write(f"- Identified recoverable / cost-avoidance: **${recoverable:,.0f}**\n")
    f.write(f"- Service areas breaching control limits: **{', '.join(breaching) or 'none'}**\n")
    f.write(f"- Highest spend-per-incident vendor: **{top_vendor.vendor}** (${top_vendor.spend_per_incident:,.0f})\n")
print("charts + results_summary written")
