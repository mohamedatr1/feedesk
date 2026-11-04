"""Read-only Rasel account check.

Usage:
    python scripts/rasel_check.py

Reads RASEL_API_KEY / RASEL_BASE_URL from .env.local. Never prints the key.
No message is sent by this script.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    path = ROOT / ".env.local"
    if not path.exists():
        raise SystemExit("Missing .env.local")
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def get(base: str, key: str, path: str) -> tuple[int, dict]:
    request = urllib.request.Request(
        base.rstrip("/") + path,
        headers={"X-API-Key": key, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw": body[:300]}
        return exc.code, payload


def main() -> int:
    env = load_env()
    key = env.get("RASEL_API_KEY", "")
    base = env.get("RASEL_BASE_URL", "https://raselsms.com")
    if not key:
        print("RASEL_API_KEY is empty", file=sys.stderr)
        return 2

    status, data = get(base, key, "/api/v2/account")
    print(f"account: HTTP {status} success={data.get('success')}")
    if status == 200:
        wallet = data.get("data", {}).get("wallet", {})
        access = data.get("data", {}).get("subscription", {}).get("access", {})
        plan = data.get("data", {}).get("subscription", {}).get("active", {})
        print(
            "wallet:",
            {k: wallet.get(k) for k in ("balance", "availableBalance", "currency")},
        )
        print("canSend:", access.get("canSend"), "plan:", plan.get("planName"), "trial:", plan.get("isTrial"))
        print("trialEnds:", plan.get("endAt"))

    status, data = get(base, key, "/api/v2/sms-senders")
    senders = data.get("data", {}).get("smsSenders", [])
    print(f"senders: HTTP {status} count={len(senders) if isinstance(senders, list) else 'n/a'}")
    if isinstance(senders, list):
        for sender in senders:
            print("  ", {k: sender.get(k) for k in ("name", "status", "isDefault")})

    status, data = get(base, key, "/api/v2/messages/policies")
    policies = data.get("data", [])
    print(f"policies: HTTP {status} count={len(policies) if isinstance(policies, list) else 'n/a'}")
    if isinstance(policies, list):
        for policy in policies:
            if policy.get("channel") == "sms_syria":
                print("  syria:", {
                    "provider": policy.get("providerKey"),
                    "enabled": policy.get("enabled"),
                    "allowedTypes": policy.get("allowedTypes"),
                    "priority": policy.get("priorityOrder"),
                })

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
