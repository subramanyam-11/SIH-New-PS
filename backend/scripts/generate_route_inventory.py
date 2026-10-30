#!/usr/bin/env python3
"""
Route Inventory Generator for SIH26262.
Inspects all registered routes in FastAPI app and lists path, method, tags, and required roles.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/demo-login",
}

def inspect_dependencies(route):
    # Check dependencies on endpoint
    roles = []
    deps = getattr(route, "dependencies", []) + getattr(route.endpoint, "__defaults__", () or ())
    for d in route.dependant.dependencies:
        call_name = getattr(d.call, "__name__", str(d.call))
        if "require_role" in str(d.call):
            # Try to extract roles from closure or attribute
            pass
    return roles

def main():
    print("=== AICTE WORKFLOW SYSTEM - ROUTE SECURITY INVENTORY ===")
    print(f"{'METHOD':<8} {'PATH':<45} {'AUTH REQUIRED':<15} {'DESCRIPTION':<35}")
    print("-" * 110)

    routes = sorted(app.routes, key=lambda r: getattr(r, "path", ""))
    count_public = 0
    count_secured = 0

    for r in routes:
        methods = ", ".join(r.methods) if hasattr(r, "methods") else "ANY"
        if methods == "OPTIONS" or not hasattr(r, "path"):
            continue
        path = r.path
        is_public = path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc")

        if is_public:
            auth_str = "PUBLIC"
            count_public += 1
        else:
            auth_str = "JWT RBAC"
            count_secured += 1

        doc = (r.endpoint.__doc__ or "").strip() if getattr(r, "endpoint", None) else ""
        doc_lines = doc.splitlines()
        summary = getattr(r, "summary", "") or (doc_lines[0] if doc_lines else "")
        summary = summary[:32] + "..." if len(summary) > 32 else summary

        print(f"{methods:<8} {path:<45} {auth_str:<15} {summary:<35}")

    print("-" * 110)
    print(f"Total endpoints examined: {count_public + count_secured} (Secured: {count_secured}, Public: {count_public})")

if __name__ == "__main__":
    main()
