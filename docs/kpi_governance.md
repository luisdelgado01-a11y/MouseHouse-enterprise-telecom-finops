# KPI Governance & Metrics Dictionary

Definitions, formulas, source system, cadence, and owner for every metric the
platform reports. Standardized definitions prevent the "two teams, two numbers"
problem in executive reporting.

## Financial
| KPI | Definition / Formula | Source | Cadence | Owner |
|---|---|---|---|---|
| Budget Variance | Actual spend − Budget | SAP GL vs Coupa | Monthly | Finance |
| Budget Variance % | (Actual − Budget) / Budget | SAP / Coupa | Monthly | Finance |
| Cost Avoidance | Σ recoverable overbillings (rate, duplicate, ghost) | Invoice audit | Monthly | FinOps |
| Cost per Incident | Telecom spend / incident count | SAP + ServiceNow | Monthly | FinOps |
| Vendor Spend | Σ billed_amount by vendor | Telecom invoices | Monthly | Vendor Mgmt |
| Forecast Accuracy | 1 − |Forecast − Actual| / Actual | Model vs SAP | Quarterly | FP&A |

## Operations
| KPI | Definition / Formula | Source | Cadence | Owner |
|---|---|---|---|---|
| Uptime % | Available time / total time | ITOM | Monthly | NetOps |
| MTBF | Mean time between failures (hours) | ITOM | Monthly | NetOps |
| MTTR | Mean time to resolve (hours) | ServiceNow | Weekly | Service Desk |
| Packet Loss % | Lost packets / sent packets | ITOM | Monthly | NetOps |
| Latency (ms) | Avg round-trip time | ITOM | Monthly | NetOps |
| Incident Volume | Count of incidents by service area | ServiceNow | Weekly | Service Desk |

## Deviation monitoring
Each service-area metric is scored against an **early-year baseline** (mean ± σ).
Any metric exceeding a **3σ control limit** is flagged as a deviation for review, giving proactive detection before an SLA breach or cost overrun.
