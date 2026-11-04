from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "apps" / "api"
sys.path.insert(0, str(API_DIR))

from app.config import settings  # noqa: E402
from app.messaging.fake import FakeProvider  # noqa: E402
from app.messaging.worker import MessagingWorker  # noqa: E402

BASE = "http://127.0.0.1:8000"
QA_DIR = ROOT / ".local" / "samples" / "qa"
MANIFEST = QA_DIR / "manifest.json"
REPORT = QA_DIR / "e2e-report.json"
ADMIN = ("qa_synthetic_admin", "QaSynthetic!2026Temp")


def client() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=300)


def login(c: httpx.Client) -> dict[str, str]:
    response = c.post(
        "/api/v1/auth/login",
        json={"username": ADMIN[0], "password": ADMIN[1]},
    )
    response.raise_for_status()
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def upload(c: httpx.Client, headers: dict[str, str], entry: dict[str, Any]) -> dict:
    path = QA_DIR / entry["file"]
    mime = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if entry["kind"] == "xlsx"
        else "application/pdf"
    )
    with path.open("rb") as handle:
        response = c.post(
            "/api/v1/imports",
            headers=headers,
            files={"file": (entry["file"], handle, mime)},
            data={
                "force_duplicate": "true",
                "duplicate_reason": "synthetic acceptance rerun",
            },
        )
    body = response.json() if response.content else {}
    if response.status_code >= 400:
        raise RuntimeError(
            f"upload {entry['file']} failed {response.status_code}: {response.text[:500]}"
        )
    return body


def process_if_needed(c: httpx.Client, headers: dict[str, str], body: dict) -> dict:
    if (body.get("total_rows") or 0) > 0:
        return body
    sheets = body.get("available_sheets") or []
    if not sheets:
        return body
    response = c.post(
        f"/api/v1/imports/{body['id']}/process",
        headers=headers,
        json={"worksheet_name": sheets[0]},
    )
    response.raise_for_status()
    return response.json()


def warnings(body: dict) -> set[str]:
    return {item.get("code") for item in body.get("warnings") or []}


def first_rows(c: httpx.Client, headers: dict[str, str], import_id: str) -> list[dict]:
    response = c.get(
        f"/api/v1/imports/{import_id}/rows",
        headers=headers,
        params={"page_size": 200},
    )
    response.raise_for_status()
    return response.json().get("items") or []


def confirm(c: httpx.Client, headers: dict[str, str], import_id: str) -> dict:
    response = c.post(
        f"/api/v1/imports/{import_id}/confirm",
        headers=headers,
        json={"acknowledge_warnings": True},
    )
    body = response.json() if response.content else {}
    if response.status_code >= 400:
        raise RuntimeError(
            f"confirm {import_id} failed {response.status_code}: {response.text[:500]}"
        )
    return body


def create_campaign(
    c: httpx.Client,
    headers: dict[str, str],
    *,
    name: str,
    import_id: str,
    template_id: str,
) -> dict:
    response = c.post(
        "/api/v1/campaigns",
        headers=headers,
        json={
            "name": name,
            "source_import_id": import_id,
            "template_id": template_id,
        },
    )
    body = response.json() if response.content else {}
    if response.status_code >= 400:
        raise RuntimeError(
            f"campaign create for {name} failed {response.status_code}: {response.text[:500]}"
        )
    return body


def submit_and_approve(
    c: httpx.Client, headers: dict[str, str], campaign: dict
) -> dict:
    submitted = c.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers=headers,
        json={"expected_revision": campaign["revision"]},
    )
    if submitted.status_code >= 400:
        raise RuntimeError(
            f"submit {campaign['id']} failed {submitted.status_code}: {submitted.text[:500]}"
        )
    body = submitted.json()
    approved = c.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers=headers,
        json={
            "expected_revision": body["revision"],
            "acknowledge_warnings": True,
        },
    )
    if approved.status_code >= 400:
        raise RuntimeError(
            f"approve {campaign['id']} failed {approved.status_code}: {approved.text[:500]}"
        )
    return approved.json()


def run_fake_worker() -> int:
    qa_settings = settings.model_copy(
        update={
            "messaging_provider": "fake",
            "messaging_enabled": True,
            "messaging_kill_switch": False,
            "messaging_rate_limit_per_second": 10000,
            "messaging_allowlist": "",
            "fake_provider_scenario": "delivered",
        }
    )
    worker = MessagingWorker(
        config=qa_settings,
        provider=FakeProvider("delivered"),
        sleep_fn=lambda _: None,
    )
    processed = 0
    for _ in range(1000):
        report = worker.run_once()
        if not report.claimed:
            break
        processed += 1
    return processed


def evaluate(
    entry: dict[str, Any],
    body: dict,
    rows: list[dict],
) -> list[str]:
    failures: list[str] = []
    total = body.get("total_rows") or 0
    if body.get("status") == "failed":
        failures.append("status=failed")
        return failures
    if total < entry["expected_min_rows"]:
        failures.append(f"rows {total} < {entry['expected_min_rows']}")
    mapping = body.get("column_mapping") or {}
    for field in ("guardian_name", "remaining_balance", "currency"):
        if field not in mapping:
            failures.append(f"missing mapping {field}")
    expected_currency = entry.get("expected_currency")
    if expected_currency:
        currencies = {
            row.get("normalized_data", {}).get("currency") for row in rows
        }
        if expected_currency not in currencies:
            failures.append(f"currency {expected_currency} absent ({sorted(c for c in currencies if c)})")
    warning_codes = warnings(body)
    # Row-level validation issues (zero/negative balance, missing or invalid
    # phone, duplicates, uncached formula) deliberately live on the row, not in
    # the document warning list.  Aggregate both for fixture acceptance.
    row_codes = {
        issue.get("code")
        for row in rows
        for issue in (row.get("validation_errors") or [])
    }
    warning_codes |= row_codes
    expected = set(entry.get("expected_warnings") or [])
    if "SCANNED_PDF" in expected and "OCR_USED" in warning_codes:
        expected.discard("SCANNED_PDF")
    missing = expected - warning_codes
    if missing:
        failures.append(f"missing warnings {sorted(missing)}")
    if entry.get("supports_full_confirm"):
        if (body.get("invalid_rows") or 0) != 0:
            failures.append(f"invalid_rows={body.get('invalid_rows')}")
        if (body.get("valid_rows") or 0) < entry["expected_min_rows"]:
            failures.append(f"valid_rows={body.get('valid_rows')} below minimum")
    return failures


def main() -> int:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    outcomes: list[dict[str, Any]] = []
    with client() as c:
        headers = login(c)
        active = c.get("/api/v1/templates/active", headers=headers)
        active.raise_for_status()
        template_id = active.json()["id"]

        for entry in entries:
            outcome: dict[str, Any] = {
                "file": entry["file"],
                "kind": entry["kind"],
                "expected_min_rows": entry["expected_min_rows"],
                "expected_currency": entry.get("expected_currency"),
                "supports_full_confirm": entry.get("supports_full_confirm"),
                "status": "FAILED",
                "failures": [],
            }
            started = time.perf_counter()
            try:
                body = upload(c, headers, entry)
                body = process_if_needed(c, headers, body)
                rows = first_rows(c, headers, body["id"])
                failures = evaluate(entry, body, rows)
                outcome.update(
                    {
                        "import_id": body["id"],
                        "status": body.get("status"),
                        "total_rows": body.get("total_rows"),
                        "valid_rows": body.get("valid_rows"),
                        "invalid_rows": body.get("invalid_rows"),
                        "warnings": sorted(warnings(body)),
                        "mapping": body.get("column_mapping"),
                        "failures": failures,
                    }
                )
                if failures:
                    outcome["status"] = "FAILED"
                elif entry.get("supports_full_confirm"):
                    confirmed = confirm(c, headers, body["id"])
                    if confirmed.get("status") != "confirmed":
                        failures.append(f"confirm status {confirmed.get('status')}")
                        outcome["status"] = "FAILED"
                    else:
                        campaign = create_campaign(
                            c,
                            headers,
                            name=f"QA {Path(entry['file']).stem}",
                            import_id=body["id"],
                            template_id=template_id,
                        )
                        approved = submit_and_approve(c, headers, campaign)
                        outcome.update(
                            {
                                "campaign_id": campaign["id"],
                                "campaign_status": approved.get("status"),
                                "campaign_revision": approved.get("revision"),
                            }
                        )
                        outcome["status"] = "STAGED_AND_APPROVED"
                else:
                    outcome["status"] = "STAGED_ONLY"
            except Exception as exc:  # noqa: BLE001
                outcome["failures"].append(str(exc)[:1000])
            outcome["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            outcomes.append(outcome)
            print(
                f"{outcome['status']:<20} {entry['file']:<52} "
                f"rows={outcome.get('total_rows')} valid={outcome.get('valid_rows')} "
                f"invalid={outcome.get('invalid_rows')} warnings={outcome.get('warnings')}"
            )
            if outcome["failures"]:
                print("  failures:", outcome["failures"])

        processed = run_fake_worker()
        print(f"fake worker processed {processed} jobs")

        campaign_results: list[dict[str, Any]] = []
        for outcome in outcomes:
            campaign_id = outcome.get("campaign_id")
            if not campaign_id:
                continue
            detail = c.get(f"/api/v1/campaigns/{campaign_id}", headers=headers)
            results = c.get(
                f"/api/v1/campaigns/{campaign_id}/results", headers=headers
            )
            if detail.status_code != 200 or results.status_code != 200:
                outcome["failures"].append("campaign results unavailable")
                outcome["campaign_verified"] = False
                continue
            detail_body = detail.json()
            result_body = results.json()
            delivered = (result_body.get("counts") or {}).get("delivered", 0)
            expected = result_body.get("message_count", 0)
            verified = (
                detail_body.get("status") == "completed"
                and delivered == expected
                and expected > 0
            )
            outcome["campaign_status"] = detail_body.get("status")
            outcome["campaign_messages"] = expected
            outcome["campaign_delivered"] = delivered
            outcome["campaign_verified"] = verified
            if not verified:
                outcome["failures"].append(
                    f"campaign not completed/delivered ({detail_body.get('status')}, {delivered}/{expected})"
                )
                outcome["status"] = "FAILED"
            campaign_results.append(
                {
                    "file": outcome["file"],
                    "campaign_id": campaign_id,
                    "status": detail_body.get("status"),
                    "messages": expected,
                    "delivered": delivered,
                    "verified": verified,
                }
            )

    final = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "fixture_count": len(entries),
        "outcomes": outcomes,
        "campaigns": campaign_results,
    }
    REPORT.write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    failed = [item for item in outcomes if item["status"] == "FAILED"]
    print(f"\nreport: {REPORT}")
    print(f"fixtures: {len(entries)}; failed: {len(failed)}; campaigns: {len(campaign_results)}")
    if failed:
        for item in failed:
            print("FAILED", item["file"], item["failures"])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
