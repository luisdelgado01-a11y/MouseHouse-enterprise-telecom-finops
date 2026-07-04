"""
PREDICTIVE: SLA breach / high-cost risk classifier.

Labels each service-area month as "high risk" when incident cost lands in the top
quartile, then trains a classifier on operational telemetry ONLY (packet loss, latency,
MTBF, uptime), deliberately excluding incident counts to avoid target leakage, so
the model acts as a genuine leading indicator of financial risk. Reports ROC-AUC (time-split), the feature that
matters most, and a next-watch list for leadership.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
PROC, ASSETS = ROOT/"data"/"processed", ROOT/"assets"
NAVY = "#1F3864"

df = pd.read_csv(PROC/"fct_service_area_monthly.csv", parse_dates=["period"]).sort_values("period")
df = df.dropna(subset=["packet_loss","latency","mtbf","uptime","incident_cost"])
feat = ["packet_loss","latency","mtbf","uptime"]  # telemetry only (no incident-count leakage)
df["high_risk"] = (df["incident_cost"] > df["incident_cost"].quantile(0.75)).astype(int)

# Time-based split: train on first 9 months, test on last 3
cut = df["period"].sort_values().unique()[9]
tr, te = df[df.period < cut], df[df.period >= cut]
clf = RandomForestClassifier(n_estimators=200, random_state=0, max_depth=4)
clf.fit(tr[feat], tr["high_risk"])
proba = clf.predict_proba(te[feat])[:,1]
try:
    auc = roc_auc_score(te["high_risk"], proba)
except ValueError:
    auc = float("nan")
imp = pd.Series(clf.feature_importances_, index=feat).sort_values(ascending=False)

print(f"Train months <{pd.Timestamp(cut).date()}, test >= that.")
print(f"Test ROC-AUC: {auc:.2f}")
print("Top risk drivers:", ", ".join(f"{k} ({v:.0%})" for k,v in imp.items()))

# Score latest month -> watch list
latest = df.groupby("service_area").tail(1).copy()
latest["risk_score"] = clf.predict_proba(latest[feat])[:,1]
watch = latest.sort_values("risk_score", ascending=False)[["service_area","risk_score"]]
print("\nNext-period risk watch list:")
for _, r in watch.iterrows():
    print(f"  {r.service_area:<20} {r.risk_score:.0%}")

fig, ax = plt.subplots(figsize=(8,4))
imp.sort_values().plot.barh(ax=ax, color=NAVY)
ax.set_title("SLA Breach Risk: Feature Importance", color=NAVY, fontweight="bold")
ax.set_xlabel("Importance")
plt.tight_layout(); plt.savefig(ASSETS/"risk_feature_importance.png", dpi=120); plt.close()

with open(ROOT/"reports"/"risk_summary.md","w") as f:
    f.write("# Predictive: SLA Breach Risk (auto-generated)\n\n")
    f.write(f"- Test ROC-AUC (time-split): **{auc:.2f}**\n")
    f.write(f"- Top driver: **{imp.index[0]}** ({imp.iloc[0]:.0%} importance)\n\n")
    f.write("**Next-period risk watch list**\n\n| Service Area | Risk |\n|---|--:|\n")
    for _, r in watch.iterrows():
        f.write(f"| {r.service_area} | {r.risk_score:.0%} |\n")
print("\nrisk model written")
