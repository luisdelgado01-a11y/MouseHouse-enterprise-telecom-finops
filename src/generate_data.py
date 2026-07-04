"""
Synthetic data generator for MouseHouse-enterprise-telecom-finops.

Creates a reproducible, seeded set of raw source tables that MIMIC the systems a
Disney Enterprise Technology / Telecom finance-analytics team works with
(ServiceNow, ITOM telemetry, telecom carrier invoices, SAP GL, Coupa POs).

All data is SIMULATED. It intentionally contains a handful of planted anomalies
(billing errors, one costly vendor, one degrading service area) so the analytics
layer has something real to "discover."
"""
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

MONTHS = pd.date_range("2025-01-01", "2025-12-01", freq="MS")
SERVICE_AREAS = ["WAN/Circuits", "Wireless/Mobile", "Voice/UCaaS",
                 "Cloud Connectivity", "Data Center Net", "Contact Center"]
VENDORS = ["NorthStar Telecom", "Meridian Networks", "BlueRidge Comms",
           "Cascade Mobile", "Atlas Fiber"]
SITES = [f"SITE-{i:02d}" for i in range(1, 21)]

# Planted anomalies
COSTLY_VENDOR = "Meridian Networks"     # ~40% above peer rate
DEGRADING_AREA = "Contact Center"        # rising packet loss + incidents
BILLING_ERROR_RATE = 0.07                # 7% of invoices mis-billed

# ---------- CMDB (assets / circuits) ----------
n_ci = 320
cmdb = pd.DataFrame({
    "ci_id": [f"CI-{i:04d}" for i in range(n_ci)],
    "service_area": rng.choice(SERVICE_AREAS, n_ci),
    "site": rng.choice(SITES, n_ci),
    "vendor": rng.choice(VENDORS, n_ci),
    "ci_type": rng.choice(["Circuit", "Router", "Switch", "Firewall", "SBC", "Mobile Plan"], n_ci),
    "install_date": pd.to_datetime("2020-01-01") + pd.to_timedelta(rng.integers(0, 1800, n_ci), unit="D"),
})
base_rate = {v: 900 for v in VENDORS}
base_rate[COSTLY_VENDOR] = int(900 * 1.40)
cmdb["monthly_cost"] = [round(base_rate[v] * rng.uniform(0.7, 1.4), 2) for v in cmdb["vendor"]]
cmdb["status"] = rng.choice(["Active", "Active", "Active", "Decommissioned"], n_ci)
cmdb.to_csv(OUT / "servicenow_cmdb.csv", index=False)

# ---------- ITOM telemetry (monthly per CI) ----------
rows = []
for _, ci in cmdb.iterrows():
    for m in MONTHS:
        degrade = 0.0
        if ci.service_area == DEGRADING_AREA:
            degrade = (m.month / 12) * 2.5   # packet loss worsens through the year
        rows.append({
            "ci_id": ci.ci_id, "service_area": ci.service_area, "period": m.date(),
            "uptime_pct": round(min(100, rng.normal(99.6, 0.3)), 3),
            "latency_ms": round(max(1, rng.normal(35 + degrade * 4, 8)), 1),
            "packet_loss_pct": round(max(0, rng.normal(0.2 + degrade, 0.15)), 3),
            "mtbf_hours": int(max(50, rng.normal(1500 - degrade * 200, 200))),
        })
itom = pd.DataFrame(rows)
itom.to_csv(OUT / "itom_telemetry.csv", index=False)

# ---------- ServiceNow incidents ----------
inc = []
iid = 0
for _, ci in cmdb.iterrows():
    lam = 0.6
    if ci.service_area == DEGRADING_AREA:
        lam = 2.0
    for m in MONTHS:
        k = rng.poisson(lam * (1 + (m.month/12 if ci.service_area == DEGRADING_AREA else 0)))
        for _ in range(k):
            iid += 1
            pr = rng.choice(["P1", "P2", "P3", "P4"], p=[0.05, 0.2, 0.45, 0.30])
            mttr = {"P1": 6, "P2": 12, "P3": 24, "P4": 48}[pr] * rng.uniform(0.5, 1.6)
            inc.append({
                "incident_id": f"INC{iid:06d}", "ci_id": ci.ci_id,
                "service_area": ci.service_area, "site": ci.site, "vendor": ci.vendor,
                "priority": pr, "opened": m.date(),
                "mttr_hours": round(mttr, 1),
                "cost_to_resolve": round(mttr * rng.uniform(85, 140), 2),
            })
pd.DataFrame(inc).to_csv(OUT / "servicenow_incidents.csv", index=False)

# ---------- Telecom carrier invoices (with planted billing errors) ----------
invs = []
vid = 0
active = cmdb[cmdb.status == "Active"]
for _, ci in cmdb.iterrows():  # include some decommissioned -> "ghost" billing
    for m in MONTHS:
        vid += 1
        contracted = ci.monthly_cost
        billed = contracted
        err_type = "none"
        if rng.random() < BILLING_ERROR_RATE:
            et = rng.choice(["rate_overcharge", "ghost_circuit", "duplicate"])
            if et == "rate_overcharge":
                billed = round(contracted * rng.uniform(1.15, 1.6), 2)
            elif et == "ghost_circuit" and ci.status == "Decommissioned":
                billed = contracted
            elif et == "duplicate":
                billed = round(contracted * 2, 2)
            err_type = et
        # skip billing most decommissioned unless it's a ghost error
        if ci.status == "Decommissioned" and err_type != "ghost_circuit":
            continue
        invs.append({
            "invoice_id": f"INV{vid:06d}", "ci_id": ci.ci_id, "vendor": ci.vendor,
            "service_area": ci.service_area, "period": m.date(),
            "contracted_rate": contracted, "billed_amount": billed,
            "ci_status": ci.status, "planted_error": err_type,
        })
pd.DataFrame(invs).to_csv(OUT / "telecom_invoices.csv", index=False)

# ---------- SAP GL (cost-center rollup) ----------
gl = (pd.DataFrame(invs)
      .groupby(["service_area", "period"], as_index=False)["billed_amount"].sum()
      .rename(columns={"billed_amount": "amount"}))
gl["cost_center"] = "CC-" + gl["service_area"].astype("category").cat.codes.astype(str).str.zfill(3)
gl["gl_account"] = "6100-Telecom"
gl.to_csv(OUT / "sap_gl.csv", index=False)

# ---------- Coupa POs / budget ----------
budget = (cmdb[cmdb.status == "Active"].groupby("service_area")["monthly_cost"].sum() * 12 * 1.05)
pd.DataFrame({
    "service_area": budget.index,
    "annual_budget": budget.round(2).values,
    "po_committed": (budget * rng.uniform(0.9, 1.0, len(budget))).round(2),
}).to_csv(OUT / "coupa_pos.csv", index=False)

print("Generated raw tables in", OUT)
for f in sorted(OUT.glob("*.csv")):
    print(" -", f.name, len(pd.read_csv(f)), "rows")
