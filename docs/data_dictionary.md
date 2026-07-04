# Data Dictionary (synthetic sources)

### servicenow_cmdb.csv
ci_id, service_area, site, vendor, ci_type, install_date, monthly_cost, status

### itom_telemetry.csv
ci_id, service_area, period, uptime_pct, latency_ms, packet_loss_pct, mtbf_hours

### servicenow_incidents.csv
incident_id, ci_id, service_area, site, vendor, priority, opened, mttr_hours, cost_to_resolve

### telecom_invoices.csv
invoice_id, ci_id, vendor, service_area, period, contracted_rate, billed_amount, ci_status, planted_error

### sap_gl.csv
service_area, period, amount, cost_center, gl_account

### coupa_pos.csv
service_area, annual_budget, po_committed

Processed marts: fct_invoice_audit, fct_service_area_monthly, fct_budget_variance, fct_vendor_scorecard.
