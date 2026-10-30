"""
Export OpenAPI JSON schema to docs/openapi.json.
Used by 'make openapi'.
"""
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app

def export_openapi():
    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs"))
    os.makedirs(docs_dir, exist_ok=True)
    out_path = os.path.join(docs_dir, "openapi.json")
    
    schema = app.openapi()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    
    print(f"✓ Exported OpenAPI {schema.get('info', {}).get('version', '')} specification ({len(schema.get('paths', {}))} endpoints) to {out_path}")

if __name__ == "__main__":
    export_openapi()
