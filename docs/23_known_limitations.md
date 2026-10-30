# Known Limitations & Production Readiness Roadmap (SIH26262)

**System:** AICTE Approval Workflow Automation, Compliance Monitoring, and Early Risk Detection  
**Evaluation Principle:** Maximum engineering honesty. No overselling. Clear demarcation between demo implementation and production infrastructure.

---

## 1. What is Mock, Simulated, or Synthetic

| Component | Current Demo Implementation | Production Deployment Requirement |
|:---|:---|:---|
| **National AICTE Integration** | High-fidelity **Mock AICTE Adapter** (`MOCK_AICTE`) running in-process, simulating inbound application sync, status callbacks, and document transfers with HMAC-SHA256 signatures and replay validation. | Direct REST/gRPC integration with AICTE’s national core database and portal backend (e-Governance cell). |
| **User & Institution Data** | Synthetic seed data: 15 technical colleges, 60 applications (`APP-10001` to `APP-10060`), and 21 user personas using fictional names (e.g. Dr. Anand V. Joshi) and `@demo.example` email domains. | Real database sync with AICTE master institutional repository across all 10,000+ approved institutions. |
| **Email & SMS Delivery** | Local `email_outbox` table and in-app notifications drawer. Simulated SMTP/SMS dispatch with delivery status tracking (`PENDING`, `SENT`, `FAILED`). | Integration with NIC Government SMS Gateway (CDAC Mobile Seva) and Government SMTP servers (`nic.in`). |
| **Antivirus & Malware Scanning** | File signature inspection (magic bytes for PDF/PNG/JPEG) and simulated detection of the industry-standard EICAR antivirus test string. | Real-time enterprise antivirus daemon (ClamAV daemon or Cloud Storage scanning API) scanning streams before disk write. |
| **Digital Signature on Orders** | Sample Letter of Approval (LoA) with `SAMPLE` watermark, official order reference, and verification QR code. | Legal India PKI DSC / Aadhaar e-Sign cryptographic token signing according to IT Act 2000. |
| **Expert Pool Data** | 15 synthetic academic experts across engineering, management, and pharmacy disciplines with simulated conflict profiles. | National AICTE Expert Peer Database with verified Aadhaar/PAN, institutional affiliation, and subject matter tags. |
| **Virtual Clock Simulation** | In-memory and database-backed clock offset (`ClockService`), allowing presenters to travel forward in time (+7 days, +30 days) to demonstrate SLA escalations. | System wall-clock (NTP synchronized to Indian Standard Time via NPL India), running cron-triggered alert engine hourly. |

---

## 2. Architectural Boundaries & Deliberate Exclusions

1. **Automation Boundary (Decision Support Only):**
   - The system **never** approves, rejects, or reverts an application automatically.
   - All state transitions that alter institutional legal rights require explicit, authenticated human officer actions.
   - Algorithmic outputs (Delay Risk Score, Smart Priority Ranking) are strictly decision-support aids.

2. **Machine Learning Model Training:**
   - We deliberately chose **not** to train a predictive machine learning model to guess approval outcomes.
   - Regulatory approvals are governed by the statutory rules of the Approval Process Handbook (APH). Using black-box models would introduce unexplainable bias and potential legal liability.
   - The only AI capability is an optional deterministic compiler that composes human-readable case summaries from verified database metadata.

3. **Storage Tier:**
   - The demo stores encrypted files on the local filesystem (`uploads/`) with AES-256-GCM encryption.
   - Production should mount distributed object storage (S3-compatible or Google Cloud Storage) with customer-managed encryption keys (KMS) and geo-redundancy.

---

## 3. Production Deployment Roadmap

If selected for national rollout, the following 5 phases are recommended:

### Phase 1: National Single Sign-On (SSO) Integration (Month 1)
- Connect to Jan Parichay / Parichay National SSO for institutional applicants and AICTE officers.
- Role-based authorization synced with AICTE active directory (Central Bureau, ROs, and Expert Committees).

### Phase 2: Core Portal Data Migration & Webhook Ingestion (Months 2–3)
- Replace `MockAICTEAdapter` with live AICTE portal webhook receivers.
- Batch ingest historical multi-year records for all 10,000+ colleges into the versioned `documents` and `undertakings` registries.

### Phase 3: High-Availability Cloud Infrastructure (Month 3)
- Deploy FastAPI microservices on Kubernetes (EKS / GKE / NIC Cloud) with Horizontal Pod Autoscaling (HPA).
- Configure PostgreSQL 16 with multi-AZ streaming replication, read-replicas for reporting, and automated point-in-time recovery (PITR).
- Redis cluster for distributed caching, session invalidation, and rate-limiting.

### Phase 4: Legal Digital Signatures & Government SMS Gateway (Month 4)
- Integrate CDAC e-Sign API for paperless, legally binding digital signing of approval letters and scrutiny checklists.
- Connect to CDAC Mobile Seva SMS gateway for instant OTPs and critical deadline escalations.

### Phase 5: National Rollout & Regional Officer Training (Months 5–6)
- Phased rollout starting with Northern and Western Regional Offices during the 2027–28 approval cycle.
- Conduct interactive workshops for Regional Officers and Scrutiny Committees.
