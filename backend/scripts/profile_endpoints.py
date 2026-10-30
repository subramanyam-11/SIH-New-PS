"""
Endpoint Performance Profiling Script for SIH26262.
Measures the latency of key list and dashboard endpoints using the test client.
Reports the 8 slowest endpoints and overall responsiveness.
"""
import os
import sys
import time

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app

def profile_endpoints():
    client = TestClient(app)
    
    # 1. Login as System Administrator (has access to all routes including audit and retention)
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "admin@demo.example",
        "password": "Password@123"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test candidate endpoints
    endpoints = [
        ("GET", "/api/v1/applications?limit=50"),
        ("GET", "/api/v1/applications?status=IN_PROGRESS&limit=50"),
        ("GET", "/api/v1/alerts?limit=50"),
        ("GET", "/api/v1/alerts/summary"),
        ("GET", "/api/v1/risk/applications?limit=50"),
        ("GET", "/api/v1/reports/pendency"),
        ("GET", "/api/v1/reports/regional-performance"),
        ("GET", "/api/v1/reports/evc"),
        ("GET", "/api/v1/reports/undertakings"),
        ("GET", "/api/v1/reports/documents"),
        ("GET", "/api/v1/reports/overdue"),
        ("GET", "/api/v1/bottlenecks"),
        ("GET", "/api/v1/evc/visits"),
        ("GET", "/api/v1/undertakings"),
        ("GET", "/api/v1/documents"),
        ("GET", "/api/v1/audit/verify-integrity"),
        ("GET", "/api/v1/audit?limit=50"),
        ("GET", "/api/v1/integration/status"),
        ("GET", "/api/v1/retention/preview"),
        ("GET", "/api/v1/applications/1/clock-segments"),
    ]

    timings = []

    print("=" * 70)
    print("  SIH26262: ENDPOINT PERFORMANCE PROFILING (DEMO DATASET)")
    print("=" * 70)

    for method, path in endpoints:
        # Warmup
        client.get(path, headers=headers)
        
        # Measure 3 runs
        latencies = []
        for _ in range(3):
            start = time.perf_counter()
            resp = client.get(path, headers=headers)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            assert resp.status_code == 200, f"Endpoint {path} failed: {resp.status_code}"
            latencies.append(elapsed_ms)
        
        avg_latency = sum(latencies) / len(latencies)
        timings.append((path, avg_latency))

    # Sort descending
    timings.sort(key=lambda x: x[1], reverse=True)

    print("\nSlowest 8 Endpoints (ranked by average latency):")
    print(f"{'Endpoint':<45} {'Avg Latency (ms)':>18}")
    print("-" * 65)
    for path, avg_ms in timings[:8]:
        print(f"{path:<45} {avg_ms:>15.2f} ms")

    print("\nSummary of all profiled endpoints:")
    print(f"  Total Endpoints Profiled : {len(endpoints)}")
    print(f"  Fastest Endpoint         : {timings[-1][0]} ({timings[-1][1]:.2f} ms)")
    print(f"  Slowest Endpoint         : {timings[0][0]} ({timings[0][1]:.2f} ms)")
    print(f"  All < 200ms Target       : {'PASSED' if timings[0][1] < 200 else 'NEEDS INDEXING'}")
    print("=" * 70)

if __name__ == "__main__":
    profile_endpoints()
