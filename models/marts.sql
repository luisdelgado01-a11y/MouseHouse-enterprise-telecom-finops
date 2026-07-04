-- Snowflake-style transformation marts (runs on DuckDB for the demo).
-- Raw CSVs are registered as views by run_marts.py before these run.

-- 1) Telecom invoice audit: contracted vs billed, classify overbilling
CREATE OR REPLACE TABLE fct_invoice_audit AS
SELECT
    invoice_id, ci_id, vendor, service_area, period,
    contracted_rate, billed_amount, ci_status,
    billed_amount - contracted_rate                       AS variance,
    CASE
        WHEN ci_status = 'Decommissioned'                 THEN 'Ghost circuit'
        WHEN billed_amount >= contracted_rate * 1.9        THEN 'Duplicate charge'
        WHEN billed_amount >  contracted_rate * 1.10       THEN 'Rate overcharge'
        ELSE 'OK'
    END AS finding
FROM telecom_invoices;

-- 2) Service-area monthly scorecard: cost + operational health
CREATE OR REPLACE TABLE fct_service_area_monthly AS
WITH spend AS (
    SELECT service_area, period, SUM(billed_amount) AS telecom_spend
    FROM telecom_invoices GROUP BY 1,2),
inc AS (
    SELECT service_area, opened AS period,
           COUNT(*) AS incidents, AVG(mttr_hours) AS avg_mttr,
           SUM(cost_to_resolve) AS incident_cost
    FROM servicenow_incidents GROUP BY 1,2),
tel AS (
    SELECT service_area, period,
           AVG(uptime_pct) AS uptime, AVG(packet_loss_pct) AS packet_loss,
           AVG(latency_ms) AS latency, AVG(mtbf_hours) AS mtbf
    FROM itom_telemetry GROUP BY 1,2)
SELECT s.service_area, s.period, s.telecom_spend,
       COALESCE(i.incidents,0) AS incidents, i.avg_mttr,
       COALESCE(i.incident_cost,0) AS incident_cost,
       t.uptime, t.packet_loss, t.latency, t.mtbf,
       s.telecom_spend / NULLIF(i.incidents,0) AS cost_per_incident
FROM spend s
LEFT JOIN inc i USING (service_area, period)
LEFT JOIN tel t USING (service_area, period);

-- 3) Budget variance (actual vs Coupa budget, annualized)
CREATE OR REPLACE TABLE fct_budget_variance AS
WITH actual AS (
    SELECT service_area, SUM(billed_amount) AS actual_spend
    FROM telecom_invoices GROUP BY 1)
SELECT c.service_area, c.annual_budget, a.actual_spend,
       a.actual_spend - c.annual_budget                    AS variance,
       (a.actual_spend - c.annual_budget)/c.annual_budget  AS variance_pct
FROM coupa_pos c JOIN actual a USING (service_area);

-- 4) Vendor scorecard
CREATE OR REPLACE TABLE fct_vendor_scorecard AS
SELECT i.vendor,
       SUM(inv.billed_amount)                    AS total_spend,
       COUNT(DISTINCT i.incident_id)             AS incidents,
       AVG(i.mttr_hours)                          AS avg_mttr,
       SUM(inv.billed_amount)/COUNT(DISTINCT i.incident_id) AS spend_per_incident
FROM servicenow_incidents i
JOIN telecom_invoices inv USING (vendor)
GROUP BY 1;
