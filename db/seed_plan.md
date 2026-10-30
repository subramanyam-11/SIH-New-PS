# Synthetic Database Seed Plan

This document details the realistic synthetic dataset to be seeded into PostgreSQL during Phase 2. The dataset is engineered to demonstrate real-world edge cases, compliance alerts, and administrative bottlenecks.

---

## 1. Regional Offices & Jurisdictions (5 Regions)

| Region ID | Code | Name & Headquarters | States Covered |
| :--- | :--- | :--- | :--- |
| 1 | `RO_NORTH` | Northern Regional Office, Kanpur | Uttar Pradesh, Uttarakhand |
| 2 | `RO_WEST` | Western Regional Office, Mumbai | Maharashtra, Goa |
| 3 | `RO_SOUTH` | Southern Regional Office, Chennai | Tamil Nadu, Puducherry |
| 4 | `RO_EAST` | Eastern Regional Office, Kolkata | West Bengal, Odisha, Bihar, Jharkhand |
| 5 | `RO_CENTRAL` | Central Regional Office, Bhopal | Madhya Pradesh, Chhattisgarh, Gujarat |

---

## 2. Institutional Directory (15 Representative Institutions)

| ID | AICTE Permanent ID | Institution Name | Region | Type | Category |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `1-102938471` | Apex Institute of Technology, Kanpur | North | Engineering | Self-Financing |
| 2 | `1-102938472` | Doon Valley College of Engineering, Dehradun | North | Engineering | Self-Financing |
| 3 | `1-102938473` | Kashi Institute of Management, Varanasi | North | Management | Self-Financing |
| 4 | `1-204958381` | Sahyadri College of Engineering & Tech, Pune | West | Engineering | Govt-Aided |
| 5 | `1-204958382` | Maratha Mandal Polytechnic, Kolhapur | West | Polytechnic | Self-Financing |
| 6 | `1-204958383` | Vidarbha Business School, Nagpur | West | Management | Self-Financing |
| 7 | `1-305849201` | Kaveri Institute of Technology, Coimbatore | South | Engineering | Self-Financing |
| 8 | `1-305849202` | Thanjavur Polytechnic College, Thanjavur | South | Polytechnic | Govt |
| 9 | `1-305849203` | Madras Academy of Computer Applications, Chennai | South | MCA | Self-Financing |
| 10 | `1-409582711` | Kalinga Institute of Engineering, Bhubaneswar | East | Engineering | Self-Financing |
| 11 | `1-409582712` | Hooghly Institute of Technology, Kolkata | East | Polytechnic | Govt-Aided |
| 12 | `1-409582713` | Patna School of Pharmacy, Patna | East | Pharmacy | Self-Financing |
| 13 | `1-508392101` | Malwa Institute of Technology, Indore | Central | Engineering | Self-Financing |
| 14 | `1-508392102` | Chhattisgarh College of Applied Sciences, Raipur | Central | Applied Arts | Self-Financing |
| 15 | `1-508392103` | Narmada Polytechnic Institute, Jabalpur | Central | Polytechnic | Govt |

---

## 3. Seed Users Hierarchy (Multi-Role Walkthroughs)

| Role | Username | Full Name | Region / Inst Assignment | Purpose in Demo |
| :--- | :--- | :--- | :--- | :--- |
| `ADMIN` | `admin@demo.example` | Dr. Rajesh Verma (System Admin) | Central Headquarters | Full config & audit inspection |
| `REGIONAL_HEAD` | `ro.north@demo.example` | Er. Sunil Trivedi (Regional Officer North) | Northern RO (Kanpur) | Regional dashboard & escalation handling |
| `REGIONAL_HEAD` | `ro.west@demo.example` | Dr. Priya Kulkarni (Regional Officer West) | Western RO (Mumbai) | Regional comparisons |
| `SCRUTINY_OFFICER` | `scrutiny1@demo.example` | Amit Sharma (Scrutiny Desk 1) | Northern RO | Testing scrutiny review & revert |
| `SCRUTINY_OFFICER` | `scrutiny2@demo.example` | Neha Joshi (Scrutiny Desk 2) | Western RO | Workload balancing demo |
| `EVC_COORDINATOR` | `evc.coord@demo.example` | Prof. K. Ramanathan (EVC Lead) | Southern RO | Scheduling queue & panel assignment |
| `COMPETENT_AUTHORITY` | `chairman@demo.example` | Dr. Anand V. Joshi (Competent Authority) | National Headquarters | National KPI dashboard & SAC/SHC orders |
| `INSTITUTION_USER` | `principal@apexkanpur.demo.example` | Dr. V. K. Saxena (Principal, Apex Kanpur) | Apex Institute (Inst #1) | Self-service portal, deficiency replies |
| `INSTITUTION_USER` | `director@sahyadri.demo.example` | Dr. S. R. Patil (Director, Sahyadri Pune) | Sahyadri College (Inst #4) | Document renewal & undertaking evidence |

---

## 4. Application Distribution (60 Total Applications)

The 60 synthetic applications are distributed across stages and time horizons to showcase realistic operational conditions:

```
Total Applications: 60
├── On-Time & Healthy: 32 applications (53%)
├── Near-Breach Warnings (Due in <= 48 hrs): 14 applications (23%)
├── Overdue & Escalated (Tier-1 / Tier-2 / Tier-3): 10 applications (17%)
└── Concluded (Approved: 3, Rejected: 1): 4 applications (7%)
```

### Stage-by-Stage Breakdown

1. **`SUBMITTED` (6 Apps)**:
   - Newly received applications ready for automated allotment to Scrutiny Desks.
2. **`SCRUTINY` (18 Apps)**:
   - 8 Healthy (entered 1-3 days ago).
   - 6 Near-Breach (entered 5-6 days ago, SLA = 7 days).
   - 4 Overdue (entered 8-12 days ago; alerts triggered to Scrutiny Officer and Regional Head).
3. **`RE_SCRUTINY` (8 Apps)**:
   - Deficiencies raised.
   - 4 waiting for institution upload; 2 where institution replied with clarification; 2 with 2nd revert cycle.
4. **`EVC_PENDING` (10 Apps)**:
   - Scrutiny cleared; waiting for EVC panel allotment.
   - 4 newly arrived (< 2 days).
   - 3 Near-Breach unscheduled (> 3 days without schedule).
   - 3 Overdue unscheduled (> 6 days; escalated to EVC Coordinator).
5. **`EVC_SCHEDULED` (6 Apps)**:
   - 3 scheduled for upcoming weekend.
   - 2 visit completed yesterday, awaiting report upload.
   - 1 inspection completed 5 days ago with missing report (Report Overdue Alert).
6. **`SAC_SHC_REVIEW` (8 Apps)**:
   - Contested deficiency cases and hearing appeals.
   - 4 hearing scheduled for upcoming council meeting.
   - 4 deliberations completed, pending final Competent Authority order.
7. **Concluded (`APPROVAL_GRANTED` / `APPROVAL_REJECTED`) (4 Apps)**:
   - Complete audit trail showing the full journey from submission to approval order issuance.

---

## 5. Seed Compliance Records

### A. EVC Visits (16 Records)
- 6 active scheduled inspections with assigned experts (Chairperson: Senior IIT/NIT Professor, 2 domain experts, 1 architect).
- 5 completed visits with uploaded report files and recommendations.
- 5 past historical records linked to completed approvals.

### B. Undertakings & Conditional Approvals (12 Records)
- **High-Impact Demo Cases**:
  - *Apex Kanpur*: "Construction of Barrier-free Divyangjan Ramp" (Due: 15 days, Status: `PENDING_SUBMISSION`).
  - *Doon Valley*: "Recruitment of 4 Cadre Faculty in CSE" (Due: Overdue by 4 days, Status: `OVERDUE` -> Escalated).
  - *Kalinga Institute*: "Establishment of High-Speed Wi-Fi in Girls' Hostel" (Evidence uploaded, Status: `UNDER_VERIFICATION`).
  - *Sahyadri Pune*: "Upgradation of Fluid Mechanics Lab Equipment" (Status: `COMPLIED`).

### C. Leases & Statutory Documents (24 Records)
- **Expiring Lease & NOC Scenarios**:
  - 4 documents **Expiring within 30 Days** (e.g., Kashi Institute Fire Safety NOC expiring in 18 days).
  - 2 documents **Expiring within 90 Days** (e.g., Doon Valley Land Lease expiring in 74 days).
  - 3 documents **Already Expired** without renewal (e.g., Vidarbha Business School Building Plan Approval expired 12 days ago; critical red alert).
  - 15 documents **Active & Healthy** (valid for 1-5 years).

### D. Active Alerts & Escalations (25 Records)
- Pre-populated alert records demonstrating the Explainable Alerts Engine:
  - 6 `NEAR_BREACH` alerts for Scrutiny Desk.
  - 5 `OVERDUE` alerts escalated to Tier-2 (`REGIONAL_HEAD`).
  - 3 `EVC_UNSCHEDULED` warnings.
  - 4 `UNDERTAKING_DUE` notifications.
  - 7 `DOCUMENT_EXPIRING` / `DOCUMENT_EXPIRED` statutory warnings.
