# 03. Roles, Permissions, and Dashboard Visibility

## 1. System Role Hierarchy

The platform defines six standard user roles aligned with statutory AICTE administration:

1. **`ADMIN` (System Administrator)**: Oversees system health, manages users/roles, updates APH configuration rules, inspects audit logs.
2. **`SCRUTINY_OFFICER` (Scrutiny Desk Officer)**: Reviews submitted dossiers, marks document compliance, records deficiencies, recommends EVC or Approval.
3. **`EVC_COORDINATOR` (Inspection Desk Coordinator)**: Manages the EVC scheduling queue, assigns inspection dates and expert panels, tracks report submissions.
4. **`REGIONAL_HEAD` (Regional Officer / Director)**: Supervises regional pendency across all stages, approves/reverts stage motions, receives Tier-2 escalations, tracks regional compliance.
5. **`COMPETENT_AUTHORITY` (Senior Management / Member Secretary / Council)**: High-level macro view of all regions, presides over SAC/SHC appeals, grants final statutory approvals, receives Tier-3 national escalations.
6. **`INSTITUTION_USER` (Institution Principal / Authorized Signatory)**: Submits applications, views progress timeline, uploads deficiency responses, submits undertaking evidence, monitors document expiries.

---

## 2. Granular RBAC Permissions Matrix

| Functional Module / Action | `ADMIN` | `SCRUTINY_OFFICER` | `EVC_COORDINATOR` | `REGIONAL_HEAD` | `COMPETENT_AUTHORITY` | `INSTITUTION_USER` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **View Dashboard** | All Regions | My Assigned Tasks | EVC Tasks | Regional Overview | National Overview | My Institution Only |
| **View Application Dossier** | Yes | Yes (Assigned) | Yes (EVC Queue) | Yes (Regional) | Yes (All) | Yes (Own) |
| **Execute Scrutiny Review** | - | **Full** | - | Review / Endorse | - | - |
| **Revert Application (Deficiencies)** | - | **Yes (Reason Req.)**| - | **Yes (Reason Req.)**| - | - |
| **Respond to Deficiencies** | - | - | - | - | - | **Yes (Uploads)** |
| **Schedule EVC Inspection** | - | - | **Full** | Approve / Re-assign| - | - |
| **Upload EVC Report & Outcome** | - | - | **Full** | Review / Endorse | - | - |
| **Preside over SAC / SHC Review** | - | - | - | Participate | **Full Decision** | Read Minutes |
| **Grant Final Approval / Rejection**| - | - | - | Recommend | **Final Authority** | View Status |
| **Track & Verify Undertakings** | View | Verify (Assigned) | - | Signoff | View | Submit Evidence |
| **Track Lease & Document Expiry**| Full | View | View | Regional Alerts | National Summary | Renew / Upload |
| **Configure APH Rules & SLAs** | **Full** | - | - | Request Changes | Approve Changes | - |
| **Inspect System Audit Logs** | **Full** | - | - | Regional Logs | Full | Own Action Log |

---

## 3. Role-Based Dashboard Experience

### A. Scrutiny Officer Dashboard
- **Focus**: Day-to-day execution and personal task queue.
- **Key Metrics**: 
  - `Assigned to Me` (Count)
  - `Due in 48 Hours` (Near-breach badge)
  - `Overdue Cases` (Red badge)
  - `Deficiency Clarifications Received` (Ready for re-scrutiny)
- **Primary Widgets**:
  - Filterable Table: Application ID, Institution Name, Pathway, Days in Scrutiny, SLA Status, Quick Action ("Start Review").
  - Deficiency checklist helper and one-click case sheet preview.

### B. EVC Coordinator Dashboard
- **Focus**: Logistics, panel assignment, and field report turnaround.
- **Key Metrics**:
  - `Awaiting Scheduling` (Queue count)
  - `Inspections Scheduled This Week`
  - `Pending Reports > 3 Days`
  - `Available Expert Pool Status`
- **Primary Widgets**:
  - EVC Queue with drag/click date picker and expert assignment modal.
  - Interactive calendar showing scheduled visits by institution district.

### C. Regional Head Dashboard
- **Focus**: Regional bottleneck elimination, supervisor signoff, and escalation handling.
- **Key Metrics**:
  - `Total Regional Applications` (Categorized by stage)
  - `Stage Bottleneck Heatmap` (Where applications are stuck the longest)
  - `Active Escalation Alerts` (Tier-2 escalations requiring intervention)
  - `Expiring Land Leases & Documents (Next 30 Days)`
- **Primary Widgets**:
  - Regional aging breakdown (0-3 days, 4-7 days, 8-14 days, 15+ days).
  - Officer workload distribution chart (cases per scrutiny officer).
  - Urgent action list (overdue scrutiny, stalled EVC reports).

### D. Competent Authority (Senior Management) Dashboard
- **Focus**: High-level national visibility, regional performance comparison, and policy compliance.
- **Key Metrics**:
  - `National Clearance Rate` (% applications processed on time)
  - `Regional Performance Comparison` (Northern vs Western vs Southern vs Eastern vs Central)
  - `SAC/SHC Hearing Docket` (Appeals queue ready for review)
  - `High-Risk Applications` (Identified by Innovation Risk Score)
- **Primary Widgets**:
  - Comparative bar charts of cycle time per region.
  - Interactive map of India highlighting regional compliance levels.
  - One-click executive summary generator for impending council meetings.

### E. Institution User Portal
- **Focus**: Transparent status tracking, timely compliance, and self-service document upkeep.
- **Key Metrics**:
  - `Application Stage Tracker` (Visual Stepper showing current milestone)
  - `Pending Action Items` (e.g., Deficiency Clarification required within 4 days)
  - `Undertakings Due for Fulfillment`
  - `Document Expiry Countdown` (Lease, Fire NOC, AICTE FDR)
- **Primary Widgets**:
  - Visual timeline with historical notes and reasons for any past revert.
  - Secure upload portal for deficiency evidence and renewed certificates.
