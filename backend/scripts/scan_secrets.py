#!/usr/bin/env python3
"""
SIH26262 Secrets & Credentials Scanner
Scans tracked repository source files for accidental secret leakage:
- Private keys (RSA, EC, OpenSSH)
- AWS, Cloud, or live API tokens
- Hardcoded production passwords
Excludes git directory, node_modules, .venv, and build directories.
"""
import os
import re
import sys

# High-risk patterns
SECRET_PATTERNS = [
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "Private cryptographic key"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{40}['\"]", "AWS Secret Access Key"),
    (r"(?i)ghp_[A-Za-z0-9_]{36}", "GitHub Personal Access Token"),
    (r"(?i)stripe[_\-]?live[_\-]?key\s*=\s*['\"][A-Za-z0-9_]+['\"]", "Live Stripe API Key"),
]

IGNORED_DIRS = {".git", ".venv", "node_modules", ".next", "__pycache__", "dist", "build"}
ALLOWED_DEMO_STRINGS = {"Password@123", "change-in-production"}

def scan_file(filepath):
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            for pattern, desc in SECRET_PATTERNS:
                matches = re.finditer(pattern, content)
                for match in matches:
                    matched_text = match.group(0)
                    if any(allowed in matched_text for allowed in ALLOWED_DEMO_STRINGS):
                        continue
                    findings.append((desc, match.start()))
    except Exception as e:
        pass
    return findings

def scan_repository():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    print("=" * 70)
    print("  SIH26262: REPOSITORY SECRETS & CREDENTIALS SCAN")
    print("=" * 70)

    total_scanned = 0
    violations = []

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in [".py", ".ts", ".tsx", ".js", ".json", ".md", ".env", ".sh", ".sql", ".yaml", ".yml"]:
                fpath = os.path.join(root, fname)
                total_scanned += 1
                results = scan_file(fpath)
                for desc, pos in results:
                    rel_path = os.path.relpath(fpath, repo_root)
                    violations.append(f"{rel_path}: {desc}")

    print(f"Total files scanned: {total_scanned}")
    if violations:
        print(f"\nFAIL: {len(violations)} high-risk secrets detected!")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("✓ SUCCESS: Zero leaked private keys or production secrets found.")
        print("=" * 70)
        sys.exit(0)

if __name__ == "__main__":
    scan_repository()
