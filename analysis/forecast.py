"""
PREDICTIVE: telecom spend forecast with Monte Carlo uncertainty band.

Fits a simple trend + seasonal-noise model to monthly telecom spend and projects
the next 6 months, wrapping the point forecast in a Monte Carlo band (P10-P90) so
leadership sees a defensible range, not a single false-precision number.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC, ASSETS = ROOT/"data"/"processed", ROOT/"assets"
rng = np.random.default_rng(11)
NAVY, TEAL = "#1F3864", "#2E86AB"

sam = pd.read_csv(PROC/"fct_service_area_monthly.csv", parse_dates=["period"])
hist = sam.groupby("period")["telecom_spend"].sum().sort_index()
y = hist.values
t = np.arange(len(y))

# Fit linear trend; residual std drives the Monte Carlo band
b1, b0 = np.polyfit(t, y, 1)
resid_std = (y - (b0 + b1*t)).std()
H = 6
future_t = np.arange(len(y), len(y)+H)
point = b0 + b1*future_t

# Monte Carlo simulation of the forecast path
sims = np.array([b0 + b1*future_t + rng.normal(0, resid_std, H) for _ in range(5000)])
p10, p50, p90 = np.percentile(sims, [10, 50, 90], axis=0)
future_idx = pd.date_range(hist.index[-1] + pd.offsets.MonthBegin(), periods=H, freq="MS")

next_q = point[:3].sum()
print(f"History months: {len(y)} | monthly trend: ${b1:,.0f}/mo")
print(f"Next-quarter spend forecast (point): ${next_q:,.0f}")
print(f"Next-quarter P10-P90 range: ${sims[:,:3].sum(1).min():,.0f} - ... "
      f"[P10 ${np.percentile(sims[:,:3].sum(1),10):,.0f}, P90 ${np.percentile(sims[:,:3].sum(1),90):,.0f}]")

fig, ax = plt.subplots(figsize=(9.5,4.8))
ax.plot(hist.index, y, "o-", color=NAVY, label="Actual")
ax.plot(future_idx, p50, "o--", color=TEAL, label="Forecast (P50)")
ax.fill_between(future_idx, p10, p90, color=TEAL, alpha=0.2, label="Monte Carlo P10-P90")
ax.set_title("Telecom Spend Forecast with Monte Carlo Band (next 6 months)",
             color=NAVY, fontweight="bold")
ax.set_ylabel("Monthly spend ($)"); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(ASSETS/"spend_forecast.png", dpi=120); plt.close()

with open(ROOT/"reports"/"forecast_summary.md","w") as f:
    f.write("# Predictive: Spend Forecast (auto-generated)\n\n")
    f.write(f"- Monthly trend: **${b1:,.0f}/month**\n")
    f.write(f"- Next-quarter point forecast: **${next_q:,.0f}**\n")
    f.write(f"- Next-quarter range (P10-P90): **${np.percentile(sims[:,:3].sum(1),10):,.0f} - "
            f"${np.percentile(sims[:,:3].sum(1),90):,.0f}**\n")
print("forecast written")
