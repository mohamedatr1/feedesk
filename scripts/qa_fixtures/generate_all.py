"""Orchestrate the FeeDesk synthetic import acceptance fixture pack.

Runs the XLSX generator, invokes Node/Playwright for the PDF fixtures, then
validates file presence/size and PDF text-layer expectations before writing
`.local/samples/qa/manifest.json`.

Usage:
    python scripts/qa_fixtures/generate_all.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
OUT_DIR = ROOT / ".local" / "samples" / "qa"
MANIFEST_PATH = OUT_DIR / "manifest.json"

# Importing the generator only reads its metadata; generation still runs in a
# child process so the orchestrator exercises the public CLI entry point.
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPT_DIR))
from generate_xlsx import FIXTURES as XLSX_FIXTURES  # noqa: E402


def _run(command: list[str], *, label: str) -> None:
    print(f"\n=== {label} ===")
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {result.returncode}")


def _normalized_text(text: str) -> str:
    return " ".join(text.split())


def _validate_xlsx(entry: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    from openpyxl import load_workbook

    path = OUT_DIR / entry["file"]
    if not path.exists():
        return "FAIL", {"reason": "missing"}
    if path.stat().st_size == 0:
        return "FAIL", {"reason": "zero bytes"}

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheets = list(workbook.sheetnames)
        if not sheets:
            return "FAIL", {"reason": "no worksheets"}
        # Confirm at least one cell can be read from each sheet.
        for sheet in sheets:
            next(workbook[sheet].iter_rows(values_only=True), None)
    finally:
        workbook.close()
    return "PASS", {"sheets": sheets, "bytes": path.stat().st_size}


def _validate_pdf(entry: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    from pypdf import PdfReader

    path = OUT_DIR / entry["file"]
    if not path.exists():
        return "FAIL", {"reason": "missing"}
    if path.stat().st_size == 0:
        return "FAIL", {"reason": "zero bytes"}

    reader = PdfReader(str(path))
    text = _normalized_text("\n".join((page.extract_text() or "") for page in reader.pages))
    expected_text = bool(entry.get("expected_text", True))
    details = {
        "pages": len(reader.pages),
        "chars": len(text),
        "bytes": path.stat().st_size,
        "expected_text": expected_text,
    }

    if expected_text and len(text) < 20:
        return "FAIL", {**details, "reason": "expected extractable text, found <20 chars"}
    if not expected_text and len(text) >= 20:
        return "FAIL", {**details, "reason": "scanned PDF unexpectedly has extractable text"}

    if entry["file"].startswith("pdf-07"):
        first_page = reader.pages[0]
        width = float(first_page.mediabox.width)
        height = float(first_page.mediabox.height)
        details["landscape"] = width > height
        if width <= height:
            return "FAIL", {**details, "reason": "expected landscape page"}

    return "PASS", details


def _manifest_entry(entry: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "file": entry["file"],
        "kind": kind,
        "expected_min_rows": entry["expected_min_rows"],
        "expected_currency": entry["expected_currency"],
        "expected_warnings": entry["expected_warnings"],
        "supports_full_confirm": entry["supports_full_confirm"],
        "notes": entry["notes"],
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    _run([sys.executable, str(SCRIPT_DIR / "generate_xlsx.py")], label="XLSX fixtures")

    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js was not found on PATH; PDF generation requires Node 20+.")
    _run([node, str(SCRIPT_DIR / "generate_pdf.mjs")], label="PDF fixtures")

    sidecar_path = OUT_DIR / ".pdf_manifest.partial.json"
    if not sidecar_path.exists():
        raise RuntimeError("PDF generator did not write .pdf_manifest.partial.json")
    with sidecar_path.open("r", encoding="utf-8") as handle:
        pdf_entries = json.load(handle)
    sidecar_path.unlink()

    manifest: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    failures = 0

    for entry in XLSX_FIXTURES:
        status, details = _validate_xlsx(entry)
        validation.append({"file": entry["file"], "status": status, **details})
        if status != "PASS":
            failures += 1
        manifest.append(_manifest_entry(entry, "xlsx"))

    for entry in pdf_entries:
        status, details = _validate_pdf(entry)
        validation.append({"file": entry["file"], "status": status, **details})
        if status != "PASS":
            failures += 1
        manifest.append(_manifest_entry(entry, "pdf"))

    with MANIFEST_PATH.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print("\n=== Fixture manifest validation ===")
    for item in validation:
        status = item["status"]
        extra = ", ".join(
            f"{key}={value}" for key, value in item.items() if key not in {"file", "status"}
        )
        print(f"{status:4}  {item['file']}  {extra}")

    print(f"\nmanifest: {MANIFEST_PATH}")
    print(f"files: {len(manifest)} ({len(XLSX_FIXTURES)} xlsx, {len(pdf_entries)} pdf)")
    print(f"validation failures: {failures}")
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
