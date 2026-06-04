#!/usr/bin/env python3
"""Test follow-up API with date filter."""
import subprocess, json, sys

# Login
r = subprocess.run(
    "curl -s -X POST http://127.0.0.1:8080/api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin123\"}'",
    shell=True, capture_output=True, text=True, timeout=10
)
ld = json.loads(r.stdout)
token = ld.get("token", "")

# Test with date range
r2 = subprocess.run(
    f"curl -s 'http://127.0.0.1:8080/api/follow-up?start_date=2026-05-12&end_date=2026-05-15' -H 'Authorization: Bearer {token}'",
    shell=True, capture_output=True, text=True, timeout=15
)
try:
    data = json.loads(r2.stdout)
    if isinstance(data, dict) and 'error' in data:
        print(f"ERROR: {data['error']}")
    else:
        print(f"Records with date filter: {len(data)}")
        print(f"Response size: {len(r2.stdout)} bytes")
        if len(data) > 0:
            print(f"First: {data[0]['patient_name']} - {data[0]['follow_up_status']}")
except json.JSONDecodeError as e:
    print(f"JSON ERROR: {e}")
    print(f"Raw: {r2.stdout[:200]}")

# Test WITHOUT date filter  
r3 = subprocess.run(
    f"curl -s 'http://127.0.0.1:8080/api/follow-up' -H 'Authorization: Bearer {token}'",
    shell=True, capture_output=True, text=True, timeout=15
)
try:
    data = json.loads(r3.stdout)
    print(f"\nRecords without date filter: {len(data)}")
except json.JSONDecodeError as e:
    print(f"JSON ERROR: {e}")
