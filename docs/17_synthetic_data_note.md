# Synthetic Data Notice & Demonstration Skew Documentation

> **Project:** AICTE Approval Workflow Automation System (SIH26262)  
> **Status:** Phase 8 Completed  
> **Notice:** All data generated and presented in this application is 100% synthetic and fictional.

---

## 1. Ethical & Statutory Disclosure

1. **Entirely Fictional Entities:**  
   All 60 applications, 15 institutions, officer profiles, committee rosters, EVC expert details, email addresses, phone numbers, and physical addresses were synthetically generated for demonstration and evaluation purposes. None correspond to actual individuals, active AICTE staff, or confidential regulatory submissions.

2. **No Actual AICTE Integration:**  
   The system interacts solely with local mock adapters and sandbox services. It does not contact or transmit data to any live AICTE or Ministry of Education production servers.

3. **Sample National Holiday Calendar Caveat:**  
   The holidays populated in the seed database (e.g. Republic Day, Independence Day, Gandhi Jayanti, Eid, Diwali) are representative samples provided to demonstrate the working-day calculation engine, weekend rollover logic, and statutory pause adjustments. They do not constitute an official Government of India gazette holiday declaration.

---

## 2. Intentional Demonstration Skews

To thoroughly demonstrate the automated governance engine, alert escalations, and innovation features during live testing, several intentional statistical skews were introduced into the seed data:

### 2.1 The Operational Bottleneck Skew
In normal steady-state operations, cases distribute evenly across stages. In the demonstration dataset (`backend/scripts/seed_demo.py`), cases are deliberately clustered in two critical approval bottlenecks:
- **Scrutiny Stage (18 applications):** Demonstrates backlogs, multiple revert tracking, and regional processing speed variance.
- **EVC Inspection Scheduling (13 applications across Pending and Scheduled):** Demonstrates panel assignment validation (conflict-of-interest checks, 3-member minimum), visit overdue rules, and coordinator capacity limits.

### 2.2 The Alert & Escalation Spread (65 Seeded Alerts)
Rather than a pristine clean state, the seed database establishes 65 active statutory alerts across all 12 alert rules:
- **17 Scrutiny Near-Breach Alerts (`RULE_SCRUTINY_NEAR_BREACH`):** Applications within 24 hours of their initial 5-day scrutiny SLA.
- **8 Scrutiny Overdue Alerts (`RULE_SCRUTINY_OVERDUE`):** Applications that have breached their stage SLA.
- **6 EVC Unscheduled Alerts (`RULE_EVC_UNSCHEDULED`):** Applications stuck in `EVC_PENDING` for $> 3$ working days without panel formation.
- **3 Multiple Revert Alerts (`RULE_MULTIPLE_REVERTS`):** Applications returned twice, warning officers that a third rejection will trigger mandatory SAC/SHC review.
- **5 Lease 90-Day Warning Alerts (`RULE_LEASE_90D`):** Institutional land leases expiring within 90 days.
- **5 Lease 30-Day Critical Alerts (`RULE_LEASE_30D`):** Institutional land leases expiring within 30 days.
- **5 Fire Safety NOC Expired Alerts (`RULE_FIRE_NOC_EXPIRED`):** Expired municipal fire NOCs requiring immediate stop-work or conditional undertakings.
- **6 Undertaking Due in 15 Days (`RULE_UNDERTAKING_DUE_15D`):** Outstanding conditional compliance undertakings approaching their deadline.
- **2 EVC Visit Overdue Alerts (`RULE_EVC_VISIT_OVERDUE`):** Scheduled inspection dates that passed without upload of the EVC report.
- **4 Undertaking Overdue Alerts (`RULE_UNDERTAKING_OVERDUE`):** Undertakings past their statutory resolution deadline.
- **2 Document Expired Alerts (`RULE_DOCUMENT_EXPIRED`):** Prescribed FDR guarantees or affiliating university NOCs past expiry.
- **2 High-Risk Early Warning Alerts (`RULE_RISK_HIGH`):** Applications #33 and #34 with dynamic risk scores $>65$ (having 2 prior reverts and stage age $\approx 2.8$ days) that are **NOT** yet overdue, demonstrating the predictive early-warning advisory feature.

---

## 3. Replication & Reset

The entire synthetic dataset can be deterministically wiped and regenerated at any time using:
```bash
make db-reset && make seed && make seed-demo
```
This guarantees an identical, pristine demonstration state for jury review and technical evaluations.
