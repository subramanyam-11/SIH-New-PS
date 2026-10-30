#!/usr/bin/env python3
"""
Unlock Demo Accounts CLI script for SIH26262.
Clears login lockout state so demo and rehearsal accounts are never blocked.
"""
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.auth import _LOGIN_ATTEMPTS, _LOGIN_LOCKOUTS

def unlock_demo_accounts():
    count = len(_LOGIN_LOCKOUTS)
    _LOGIN_ATTEMPTS.clear()
    _LOGIN_LOCKOUTS.clear()
    print(f"✓ Successfully unlocked all demo accounts (cleared {count} active lockouts).")
    print("✓ All 8 demo personas are ready for presentation login.")
    return 0

if __name__ == "__main__":
    sys.exit(unlock_demo_accounts())
