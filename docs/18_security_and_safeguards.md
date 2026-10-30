# Security, Privacy & Safeguards Matrix

> **Project:** AICTE Approval Workflow Automation System (SIH26262)  
> **Reference:** Build Plan v2 Section 10 (Security, Privacy & Safeguards)  
> **Status:** Phase 8 Completed  

---

## 1. Compliance & Implementation Mapping Table

| Section 10 Area | Requirement (Build Plan v2) | Status | Honest Technical Implementation Summary |
| :--- | :--- | :--- | :--- |
| **Access Control** | Role-based access on every endpoint and screen; institutions see only their own records. | **Implemented** | JWT tokens with role/regional scoping enforced on 90+ endpoints; institutions cannot access other institutions' records or files. |
| **Login Hardening** | Abuse prevention and credential protection. | **Implemented** | Failed attempt rate limiting with 15-minute temporary lockout after 5 consecutive failures, plus password complexity enforcement for production accounts. |
| **Document Security: Encryption at Rest** | Secure storage and encryption of files. | **Implemented** | AES-256-GCM authenticated encryption at rest using the Python `cryptography` library with unique 96-bit nonces and key rotation metadata stored per file. |
| **Document Security: Content Inspection** | Uploads limited by file type, size, and scanned before storage. | **Implemented** | Magic-byte verification (`%PDF`, `\x89PNG`, `\xff\xd8\xff`), single-extension enforcement (blocking double extensions like `.pdf.exe`), and strict 10 MB size limits. |
| **Document Security: Anti-Malware Scanner** | Scan uploaded files for malware before permanent storage. | **Demo-level** | Integrated `DemoScanner` detects standard EICAR test signatures and scripts; full ClamAV daemon adapter is ready for production socket attachment. |
| **Transport Security (TLS / In-Transit)** | Encryption in transit over public networks. | **Production recommendation** | Local prototype operates over HTTP; production deployments must terminate TLS 1.3 via reverse proxy (Caddy/Nginx sample provided below). |
| **Traceability: Database Append-Only** | Immutability and auditability of statutory records. | **Implemented** | PostgreSQL triggers block `UPDATE` and `DELETE` on `audit_log`, while a cryptographic SHA-256 hash chain guarantees tamper-evidence. |
| **Traceability: View Auditing** | Log views of sensitive records (dossiers, files, exports). | **Implemented** | Access to sensitive records is logged to `audit_log` with an in-memory 60-second deduplication cache to prevent log flooding. |
| **Data Protection: Retention Policy** | Minimum data collected; configurable retention periods. | **Demo-level** | Admin retention configuration and dry-run preview screen (`/admin/retention`) are fully functional; automatic deletion is disabled by design in this prototype. |
| **External Integration** | Connect to external AICTE portal with integrity and replay guards. | **Demo-level** | `MockAicteAdapter` implements synthetic lookup/push with HMAC-SHA256 signature verification, 300-second drift replay guards, and idempotency caching. |
| **Human Oversight** | Scrutiny, inspections, and final decisions remain with competent authorities. | **Implemented** | AI summaries, bottleneck scores, and alert rankings are strictly advisory and carry prominent "Decision support only" labels. |
| **Regulatory Alignment** | Configurable rules and timelines matching the applicable APH. | **Implemented** | Stage SLA durations, escalation matrix levels, holiday calendars, and risk weights are completely configurable via database and admin settings. |

---

## 2. Encryption in Transit (TLS Deployment Architecture)

The local development and testing environment deliberately operates over plain HTTP to simplify workstation evaluation without self-signed certificate warnings. In any staging or production rollout, encryption in transit must be provided by a reverse proxy terminating HTTPS before traffic reaches FastAPI and Next.js.

### 2.1 Recommended Production Caddy Configuration (`Caddyfile`)
```caddy
approvals.aicte-india.org {
    # Automatic TLS certificate issuance and renewal via Let's Encrypt / ZeroSSL
    encode gzip zstd

    # Security Headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # Reverse proxy API requests to FastAPI backend
    handle /api/* {
        reverse_proxy localhost:8000
    }

    # Reverse proxy UI requests to Next.js frontend
    handle /* {
        reverse_proxy localhost:3000
    }
}
```

### 2.2 Alternative Nginx Reverse Proxy Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name approvals.aicte-india.org;

    ssl_certificate /etc/ssl/certs/aicte_cert.pem;
    ssl_certificate_key /etc/ssl/private/aicte_key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```
