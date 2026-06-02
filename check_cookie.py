#!/usr/bin/env python3
"""Print how long the LEETCODE_SESSION cookie has left.

Used by the GitHub Action to warn you before the cookie expires (and the sync
starts failing). Decodes the JWT payload locally — nothing is sent anywhere.
Never fails the build itself; the actual sync failing is the hard signal.
"""
import base64
import json
import os
import sys
import time


def main() -> int:
    tok = os.getenv("LEETCODE_SESSION")
    if not tok or tok.count(".") < 2:
        print("LEETCODE_SESSION not set or not a JWT; skipping expiry check.")
        return 0
    try:
        payload = tok.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        refreshed = int(float(data["refreshed_at"]))
        lifetime = int(data["_session_expiry"])
        days_left = (refreshed + lifetime - time.time()) / 86400
    except Exception as exc:  # malformed token — don't block the run
        print(f"Could not parse cookie expiry: {exc}")
        return 0

    msg = f"LEETCODE_SESSION cookie has ~{days_left:.1f} days left."
    print(msg)
    if days_left < 3:
        # GitHub Actions warning annotation -> shows up prominently in the run.
        print(f"::warning title=LeetCode cookie expiring::{msg} "
              f"Refresh the LEETCODE_SESSION/LEETCODE_CSRFTOKEN repo secrets soon.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
