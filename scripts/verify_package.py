"""
SIH26262 Release Package Verification Script
Validates that a submission zip file contains ONLY clean source code and zero
prohibited artifacts (.env secrets, uploads, node_modules, .venv, .next, __pycache__, keys, .git).
"""
import sys
import os
import zipfile
import re

FORBIDDEN_PREFIXES_OR_SUBSTRINGS = [
    "uploads/",
    "backend/uploads/",
    "node_modules/",
    "frontend/node_modules/",
    ".venv/",
    "backend/.venv/",
    ".next/",
    "frontend/.next/",
    "__pycache__/",
    ".git/",
    ".pytest_cache/",
]

KEY_EXTENSIONS = [".pem", ".key", ".pkcs12", ".pfx", "id_rsa", "id_ed25519"]

def verify_zip(zip_path: str) -> bool:
    if not os.path.exists(zip_path):
        print(f"ERROR: Zip file not found: {zip_path}")
        return False

    print("=" * 70)
    print(f"  VERIFYING RELEASE ARCHIVE: {zip_path}")
    print("=" * 70)

    size_bytes = os.path.getsize(zip_path)
    size_mb = size_bytes / (1024 * 1024)

    violations = []

    with zipfile.ZipFile(zip_path, 'r') as zf:
        infolist = zf.infolist()
        total_files = len(infolist)

        for info in infolist:
            name = info.filename.replace("\\", "/")

            # Check .env rules: only .env.example is allowed
            basename = os.path.basename(name)
            if basename.startswith(".env"):
                if basename != ".env.example":
                    violations.append(f"Prohibited environment file: {name}")

            # Check directory prefixes/substrings
            for forbidden in FORBIDDEN_PREFIXES_OR_SUBSTRINGS:
                if forbidden in name or name.startswith(forbidden):
                    violations.append(f"Prohibited directory/cache artifact ({forbidden}): {name}")
                    break

            # Check key material
            for key_ext in KEY_EXTENSIONS:
                if name.endswith(key_ext) or key_ext in basename:
                    violations.append(f"Prohibited cryptographic key material: {name}")
                    break

    if violations:
        print(f"\n❌ VERIFICATION FAILED: {len(violations)} prohibited item(s) found in archive:\n")
        for v in violations[:20]:
            print(f"  - {v}")
        if len(violations) > 20:
            print(f"  ... and {len(violations) - 20} more violations.")
        return False

    print(f"✓ Total files in archive : {total_files}")
    print(f"✓ Archive file size      : {size_bytes:,} bytes ({size_mb:.2f} MB)")
    print("✓ Zero prohibited files or secrets detected (.env, uploads, .venv, node_modules, keys, caches clean).")
    print("=" * 70)
    print("  ✓ SUCCESS: RELEASE PACKAGE IS CLEAN AND SAFE FOR SUBMISSION")
    print("=" * 70)
    return True

if __name__ == "__main__":
    archive_file = sys.argv[1] if len(sys.argv) > 1 else "sih26262_release.zip"
    if not verify_zip(archive_file):
        sys.exit(1)
    sys.exit(0)
