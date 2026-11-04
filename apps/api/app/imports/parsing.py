from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pdfplumber
from openpyxl import load_workbook

from ..config import settings
from .constants import MESSAGES_AR
from .errors import ImportParseError
from .normalization import (
    auto_suggest_mapping,
    clean_text,
    detect_currency,
    normalize_pdf_cell,
    normalize_phone,
    parse_currency,
    parse_money,
    resolve_mapping,
    strip_arabic_marks,
    unify_arabic_letters,
)
from .ocr import is_available as ocr_is_available
from .ocr import ocr_page

_HEADER_SCAN_LIMIT = 20
_PDF_HEADER_SCAN_LIMIT = 5
_PDF_TEXT_THRESHOLD = 10
_SHEET_SCAN_LIMIT = 30
_SHEET_SCORE_FIELDS = (
    "guardian_name",
    "guardian_phone",
    "remaining_balance",
    "total_fee",
    "amount_paid",
    "currency",
)
_SYNTHETIC_CURRENCY_HEADER = "العملة (مستنتجة)"
_SYNTHETIC_HEADER_PREFIX = "عمود"

_TEXT_PATTERN = re.compile(r"[A-Za-z\u0600-\u06FF]")
_DATE_PATTERN = re.compile(
    r"(?:\d{4}\s*[-/]\s*\d{1,2}|\d{1,2}\s*[-/]\s*\d{4})"
)
_PERIOD_PATTERN = re.compile(
    r"(?:فصل|ترم|شهر|أيلول|ايلول|كانون|شباط|آذار|اذار|نيسان|أيار|ايار|"
    r"حزيران|تموز|آب|اب|تشرين|يناير|فبراير|مارس|أبريل|ابريل|مايو|"
    r"يونيو|يوليو|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر)",
    re.IGNORECASE,
)


@dataclass
class ParsedRow:
    raw_data: dict[str, Any]
    warnings: list[dict[str, Any]] = field(default_factory=list)
    source_row_number: int | None = None
    source_page_number: int | None = None


@dataclass
class ParsedDocument:
    file_type: str
    mapping: dict[str, str]
    rows: list[ParsedRow]
    warnings: list[dict[str, Any]]
    available_sheets: list[str] | None = None
    worksheet_name: str | None = None


@dataclass
class _Layout:
    headers: list[str]
    mapping: dict[str, str]
    data_start: int
    heuristic: bool = False
    data_rows: list[list[str]] | None = None


def _warning(
    code: str,
    *,
    severity: str = "warning",
    details: dict[str, Any] | None = None,
    message_ar: str | None = None,
) -> dict[str, Any]:
    warning = {
        "code": code,
        "message_ar": message_ar or MESSAGES_AR.get(code, code),
        "severity": severity,
    }
    if details is not None:
        warning["details"] = details
    return warning


def _append_warning(warnings: list[dict[str, Any]], code: str) -> None:
    if not any(item.get("code") == code for item in warnings):
        warnings.append(_warning(code))


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float):
        # Never round-trip money through a binary float in the API payload.
        return repr(value)
    return str(value)


def list_xlsx_sheets(path: Path) -> list[str]:
    # Guard stored files too: parse_xlsx() reaches this before reading cells.
    from .storage import ensure_xlsx_file_safe

    ensure_xlsx_file_safe(path)
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        return list(workbook.sheetnames)
    finally:
        workbook.close()


def _unique_headers(values: list[Any]) -> list[str]:
    last_index = -1
    for index, value in enumerate(values):
        if clean_text(value):
            last_index = index
    headers: list[str] = []
    counts: dict[str, int] = {}
    for index in range(last_index + 1):
        header = clean_text(values[index]) or f"عمود {index + 1}"
        count = counts.get(header, 0) + 1
        counts[header] = count
        headers.append(header if count == 1 else f"{header} ({count})")
    return headers


def _synthetic_headers(width: int) -> list[str]:
    return [f"{_SYNTHETIC_HEADER_PREFIX} {index + 1}" for index in range(width)]


def _max_width(rows: list[list[Any]]) -> int:
    return max((len(row) for row in rows), default=0)


def _first_data_index(rows: list[list[Any]]) -> int | None:
    """Locate the first row that looks like data, skipping single-cell titles."""
    first_non_empty: int | None = None
    for index, row in enumerate(rows):
        cells = sum(1 for value in row if clean_text(value))
        if cells == 0:
            continue
        if first_non_empty is None:
            first_non_empty = index
        if cells >= 2:
            return index
    return first_non_empty


def _infer_header(
    rows: list[list[str]],
    *,
    scan_limit: int,
) -> tuple[int, list[str], dict[str, str]]:
    best: tuple[float, int, list[str], dict[str, str]] | None = None
    for index, row in enumerate(rows[:scan_limit]):
        headers = _unique_headers(row)
        if not headers:
            continue
        mapping = auto_suggest_mapping(headers)
        if len(mapping) < 2:
            continue
        if "guardian_name" not in mapping and "remaining_balance" not in mapping:
            continue
        score = float(len(mapping))
        if "guardian_name" in mapping:
            score += 1.0
        if "remaining_balance" in mapping:
            score += 1.0
        if "currency" in mapping:
            score += 0.5
        if best is None or score > best[0]:
            best = (score, index, headers, mapping)
    if best is None:
        raise ImportParseError("HEADER_NOT_FOUND")
    _, index, headers, mapping = best
    return index, headers, mapping


def _try_infer_header(
    rows: list[list[str]],
    *,
    scan_limit: int,
) -> tuple[int, list[str], dict[str, str]] | None:
    try:
        return _infer_header(rows, scan_limit=scan_limit)
    except ImportParseError:
        return None


def _sufficient_mapping(mapping: dict[str, str]) -> bool:
    return "guardian_name" in mapping and "remaining_balance" in mapping


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", clean_text(value))


def _is_phone_value(value: Any) -> bool:
    # Money values of six or seven digits can look like *possible* phone
    # numbers, so require a realistic phone length before classifying.
    if len(_digits(value)) < 9:
        return False
    return normalize_phone(value).normalized is not None


def _is_money_value(value: Any) -> bool:
    return parse_money(value).status == "ok"


def _is_currency_value(value: Any) -> bool:
    text = clean_text(value)
    if not text:
        return False
    # Cells such as "ل.س 620,000" contain both a currency token and a money
    # value.  Treat them as money so headerless layouts keep the balance
    # column instead of dropping it into a currency-only column.
    if parse_money(text).status == "ok":
        return False
    return parse_currency(text) is not None or detect_currency(text) is not None


def _has_letters(value: Any) -> bool:
    return bool(_TEXT_PATTERN.search(clean_text(value)))


def _is_period_value(value: Any) -> bool:
    text = clean_text(value)
    if not text:
        return False
    return bool(_DATE_PATTERN.search(text) or _PERIOD_PATTERN.search(text))


def _ratio(values: list[Any], predicate: Any) -> float:
    non_empty = [value for value in values if clean_text(value)]
    if not non_empty:
        return 0.0
    return sum(1 for value in non_empty if predicate(value)) / len(non_empty)


def _column_values(rows: list[list[Any]], index: int) -> list[Any]:
    return [row[index] if index < len(row) else None for row in rows]


def _find_balanced_triple(
    money_columns: list[int],
    columns: dict[int, list[Any]],
) -> tuple[int, int, int] | None:
    candidates = money_columns[:6]
    if len(candidates) < 3:
        return None
    for total_index, paid_index, remaining_index in itertools.permutations(
        candidates, 3
    ):
        checked = 0
        matched = True
        length = len(columns[total_index])
        for row_index in range(length):
            values = [
                columns[total_index][row_index],
                columns[paid_index][row_index],
                columns[remaining_index][row_index],
            ]
            if not all(clean_text(value) for value in values):
                continue
            total = parse_money(values[0])
            paid = parse_money(values[1])
            remaining = parse_money(values[2])
            if (
                total.status != "ok"
                or paid.status != "ok"
                or remaining.status != "ok"
                or total.value is None
                or paid.value is None
                or remaining.value is None
            ):
                continue
            checked += 1
            if total.value - paid.value != remaining.value:
                matched = False
                break
        if matched and checked >= 2:
            return total_index, paid_index, remaining_index
    return None


def _map_money_columns(
    mapping: dict[str, str],
    headers: list[str],
    money_columns: list[int],
    columns: dict[int, list[Any]],
    existing: dict[str, str],
) -> None:
    if not money_columns:
        return
    index_by_header = {header: index for index, header in enumerate(headers)}
    hint_total = index_by_header.get(existing.get("total_fee", ""))
    hint_paid = index_by_header.get(existing.get("amount_paid", ""))
    hint_remaining = index_by_header.get(existing.get("remaining_balance", ""))

    if len(money_columns) >= 3:
        triple = _find_balanced_triple(money_columns, columns)
        if triple is not None:
            total_index, paid_index, remaining_index = triple
            mapping.setdefault("total_fee", headers[total_index])
            mapping.setdefault("amount_paid", headers[paid_index])
            mapping.setdefault("remaining_balance", headers[remaining_index])
            return

    if len(money_columns) == 1:
        mapping.setdefault("remaining_balance", headers[money_columns[0]])
        return

    remaining_index: int | None = None
    if hint_remaining in money_columns:
        remaining_index = hint_remaining
    elif hint_total in money_columns and hint_paid in money_columns:
        remaining_index = next(
            (
                index
                for index in money_columns
                if index not in {hint_total, hint_paid}
            ),
            money_columns[-1],
        )
    elif hint_total in money_columns:
        remaining_index = next(
            (index for index in money_columns if index != hint_total),
            money_columns[-1],
        )
    elif hint_paid in money_columns:
        remaining_index = next(
            (index for index in money_columns if index != hint_paid),
            money_columns[-1],
        )
    else:
        remaining_index = money_columns[-1]

    mapping.setdefault("remaining_balance", headers[remaining_index])
    others = [index for index in money_columns if index != remaining_index]
    if not others:
        return
    if hint_total in money_columns and hint_total != remaining_index:
        mapping.setdefault("total_fee", headers[hint_total])
    elif hint_paid in money_columns and hint_paid != remaining_index:
        mapping.setdefault("amount_paid", headers[hint_paid])
    else:
        mapping.setdefault("total_fee", headers[others[0]])


def _heuristic_mapping(
    rows: list[list[Any]],
    headers: list[str],
    existing: dict[str, str] | None = None,
) -> dict[str, str]:
    """Infer a mapping from sampled values when headers are missing/partial."""
    existing = dict(existing or {})
    mapping: dict[str, str] = dict(existing)
    column_count = len(headers)
    if column_count == 0:
        return mapping

    sample = [row for row in rows if any(clean_text(value) for value in row)][:30]
    if not sample:
        return mapping

    columns = {
        index: _column_values(sample, index) for index in range(column_count)
    }
    active = [
        index
        for index in range(column_count)
        if any(clean_text(value) for value in columns[index])
    ]

    phone_columns: list[int] = []
    currency_columns: list[int] = []
    money_columns: list[int] = []
    period_columns: list[int] = []
    text_columns: list[int] = []

    for index in active:
        values = columns[index]
        if _ratio(values, _is_currency_value) >= 0.6:
            currency_columns.append(index)
            continue
        if _ratio(values, _is_phone_value) >= 0.6:
            phone_columns.append(index)
            continue
        if _ratio(values, _is_money_value) >= 0.6:
            money_columns.append(index)
            continue
        if _ratio(values, _is_period_value) >= 0.5:
            period_columns.append(index)
            continue
        if _ratio(values, _has_letters) >= 0.5:
            text_columns.append(index)

    # OCR-mangled phone headers and partially invalid numbers often fail the
    # strict phone check.  Fall back to plain digit length, but never steal a
    # column already classified as money or currency.
    digit_phone_columns = [
        index
        for index in active
        if index not in money_columns and index not in currency_columns
        and _ratio(
            columns[index],
            lambda value: len(_digits(value)) >= 9,
        )
        >= 0.5
    ]

    if "currency" not in mapping and currency_columns:
        mapping["currency"] = headers[currency_columns[0]]
    if "guardian_phone" not in mapping:
        if phone_columns:
            mapping["guardian_phone"] = headers[phone_columns[0]]
        elif digit_phone_columns:
            mapping["guardian_phone"] = headers[digit_phone_columns[0]]

    _map_money_columns(mapping, headers, money_columns, columns, existing)

    if "fee_period" not in mapping and period_columns:
        mapping["fee_period"] = headers[period_columns[0]]

    used_headers = set(mapping.values())
    name_columns = [
        index for index in text_columns if headers[index] not in used_headers
    ]
    if "guardian_name" not in mapping and name_columns:
        mapping["guardian_name"] = headers[name_columns.pop(0)]
    if "student_name" not in mapping and name_columns:
        mapping["student_name"] = headers[name_columns.pop(0)]

    return mapping


def _merge_mapping(
    headers: list[str],
    auto_mapping: dict[str, str],
    provided: dict[str, str] | None,
) -> dict[str, str]:
    accepted = dict(provided or {})
    # A currency column injected on a previous pass does not exist in the
    # workbook/PDF itself; drop it and let the document/school currency be
    # inferred again instead of rejecting the whole mapping.
    currency_source = accepted.get("currency")
    if currency_source and currency_source.startswith(
        _SYNTHETIC_CURRENCY_HEADER
    ):
        accepted.pop("currency", None)

    resolved = resolve_mapping(headers, accepted)
    final_mapping = dict(auto_mapping)
    final_mapping.update(resolved)
    for canonical, source in accepted.items():
        if not source:
            final_mapping.pop(canonical, None)
    return final_mapping


def _document_currency(
    raw_rows: list[list[Any]],
    data_start: int,
) -> str | None:
    # Title rows and the header row only; data values must never override the
    # currency column.
    for row in raw_rows[:data_start]:
        for value in row:
            detected = detect_currency(value)
            if detected is not None:
                return detected
    return None


def _synthetic_currency_header(used_headers: set[str]) -> str:
    header = _SYNTHETIC_CURRENCY_HEADER
    suffix = 2
    while header in used_headers:
        header = f"{_SYNTHETIC_CURRENCY_HEADER} ({suffix})"
        suffix += 1
    return header


def _apply_currency(
    rows: list[ParsedRow],
    mapping: dict[str, str],
    *,
    document_currency: str | None,
    default_currency: str | None,
    warnings: list[dict[str, Any]],
    used_headers: set[str],
) -> None:
    if not rows:
        return
    target = document_currency or default_currency
    if target is None:
        return

    currency_header = mapping.get("currency")
    if currency_header is not None:
        filled = False
        for row in rows:
            value = row.raw_data.get(currency_header)
            # OCR noise such as ``5``, ``Uso`` or ``dail`` must not survive as
            # the row currency.  A real, different currency value is kept.
            if parse_currency(value) is None:
                row.raw_data[currency_header] = target
                filled = True
        if filled and document_currency is None:
            _append_warning(warnings, "CURRENCY_FROM_SCHOOL_SETTINGS")
        return

    header = _synthetic_currency_header(used_headers)
    mapping["currency"] = header
    used_headers.add(header)
    for row in rows:
        row.raw_data[header] = target
    if document_currency is None:
        _append_warning(warnings, "CURRENCY_FROM_SCHOOL_SETTINGS")


def _sheet_sample_rows(
    workbook: Any,
    worksheet_name: str,
    limit: int,
) -> list[list[Any]]:
    worksheet = workbook[worksheet_name]
    rows: list[list[Any]] = []
    for index, row in enumerate(worksheet.iter_rows(values_only=True)):
        rows.append(list(row))
        if index >= limit:
            break
    return rows


def _sheet_score(rows: list[list[Any]]) -> tuple[int, int]:
    text_rows = [[clean_text(value) for value in row] for row in rows]
    found = _try_infer_header(text_rows, scan_limit=_SHEET_SCAN_LIMIT)
    if found is None:
        first_data = _first_data_index(rows)
        if first_data is None:
            return 0, 0
        headers = _synthetic_headers(_max_width(rows))
        mapping = _heuristic_mapping(rows[first_data:], headers)
        mapping_count = sum(
            1 for canonical in _SHEET_SCORE_FIELDS if canonical in mapping
        )
        data_rows = sum(
            1
            for row in rows[first_data:]
            if any(clean_text(value) for value in row)
        )
        return mapping_count, data_rows
    header_index, _headers, mapping = found
    mapping_count = sum(
        1 for canonical in _SHEET_SCORE_FIELDS if canonical in mapping
    )
    data_rows = sum(
        1
        for row in rows[header_index + 1 :]
        if any(clean_text(value) for value in row)
    )
    return mapping_count, data_rows


def _select_statement_sheet(path: Path, sheets: list[str]) -> str:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        best_name = sheets[0]
        best_score = (-1, -1)
        for sheet_name in sheets:
            rows = _sheet_sample_rows(workbook, sheet_name, _SHEET_SCAN_LIMIT)
            score = _sheet_score(rows)
            if score > best_score:
                best_score = score
                best_name = sheet_name
        return best_name
    finally:
        workbook.close()


def _read_sheet_rows(path: Path, worksheet_name: str, limit: int) -> list[list[Any]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook[worksheet_name]
        rows: list[list[Any]] = []
        for index, row in enumerate(worksheet.iter_rows(values_only=True)):
            rows.append(list(row))
            if index >= limit:
                break
        return rows
    finally:
        workbook.close()


def _infer_xlsx_layout(
    raw_rows: list[list[Any]],
    text_rows: list[list[str]],
    warnings: list[dict[str, Any]],
) -> _Layout | None:
    found = _try_infer_header(text_rows, scan_limit=_HEADER_SCAN_LIMIT)
    if found is None:
        first_data = _first_data_index(raw_rows)
        if first_data is None:
            return None
        headers = _synthetic_headers(_max_width(raw_rows))
        auto_mapping = _heuristic_mapping(raw_rows[first_data:], headers)
        warnings.append(_warning("HEADER_NOT_FOUND"))
        return _Layout(
            headers=headers,
            mapping=auto_mapping,
            data_start=first_data,
            heuristic=True,
        )

    header_index, headers, auto_mapping = found
    data_start = header_index + 1
    if not _sufficient_mapping(auto_mapping):
        heuristic = _heuristic_mapping(
            raw_rows[data_start:], headers, auto_mapping
        )
        auto_mapping = {**heuristic, **auto_mapping}
        warnings.append(_warning("HEADER_NOT_FOUND"))
        return _Layout(
            headers=headers,
            mapping=auto_mapping,
            data_start=data_start,
            heuristic=True,
        )
    return _Layout(
        headers=headers,
        mapping=auto_mapping,
        data_start=data_start,
        heuristic=False,
    )


def _merged_values(path: Path, worksheet_name: str) -> dict[tuple[int, int], Any]:
    workbook = load_workbook(path, read_only=False, data_only=False)
    try:
        worksheet = workbook[worksheet_name]
        values: dict[tuple[int, int], Any] = {}
        for merged in worksheet.merged_cells.ranges:
            top_left = worksheet.cell(merged.min_row, merged.min_col).value
            if top_left is None:
                continue
            for row in range(merged.min_row, merged.max_row + 1):
                for column in range(merged.min_col, merged.max_col + 1):
                    if (row, column) == (merged.min_row, merged.min_col):
                        continue
                    values[(row, column)] = top_left
        return values
    finally:
        workbook.close()


def _formula_cells(path: Path, worksheet_name: str) -> set[tuple[int, int]]:
    workbook = load_workbook(path, read_only=False, data_only=False)
    try:
        worksheet = workbook[worksheet_name]
        coordinates: set[tuple[int, int]] = set()
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.data_type == "f" or (
                    isinstance(cell.value, str) and cell.value.startswith("=")
                ):
                    coordinates.add((cell.row, cell.column))
        return coordinates
    finally:
        workbook.close()


def parse_xlsx(
    path: Path,
    *,
    worksheet_name: str | None,
    mapping: dict[str, str] | None,
    max_rows: int,
    default_currency: str | None = None,
) -> ParsedDocument:
    sheets = list_xlsx_sheets(path)
    if not sheets:
        raise ImportParseError("SHEET_EMPTY")

    warnings: list[dict[str, Any]] = []
    if worksheet_name is None:
        if len(sheets) > 1:
            worksheet_name = _select_statement_sheet(path, sheets)
            warnings.append(
                _warning(
                    "SHEET_AUTO_SELECTED",
                    details={"worksheet_name": worksheet_name},
                    message_ar=(
                        f"{MESSAGES_AR['SHEET_AUTO_SELECTED']} "
                        f"الورقة المختارة: {worksheet_name}."
                    ),
                )
            )
        else:
            worksheet_name = sheets[0]
    if worksheet_name not in sheets:
        raise ImportParseError(
            "SHEET_NOT_FOUND", details={"available_sheets": sheets}
        )

    raw_rows = _read_sheet_rows(
        path, worksheet_name, _HEADER_SCAN_LIMIT + max_rows + 2
    )
    non_empty = [
        row for row in raw_rows if any(clean_text(value) for value in row)
    ]
    if not non_empty:
        return ParsedDocument(
            file_type="xlsx",
            mapping={},
            rows=[],
            warnings=[_warning("SHEET_EMPTY")],
            available_sheets=sheets,
            worksheet_name=worksheet_name,
        )

    text_rows = [[clean_text(value) for value in row] for row in raw_rows]
    layout = _infer_xlsx_layout(raw_rows, text_rows, warnings)
    if layout is None:
        return ParsedDocument(
            file_type="xlsx",
            mapping={},
            rows=[],
            warnings=[_warning("SHEET_EMPTY")],
            available_sheets=sheets,
            worksheet_name=worksheet_name,
        )

    headers = layout.headers
    final_mapping = _merge_mapping(headers, layout.mapping, mapping)
    document_currency = _document_currency(raw_rows, layout.data_start)

    merged_values = _merged_values(path, worksheet_name)
    formula_cells = _formula_cells(path, worksheet_name)

    rows: list[ParsedRow] = []
    for row_index in range(layout.data_start, len(raw_rows)):
        source_values = list(raw_rows[row_index])
        source_row_number = row_index + 1
        merged_flags = False
        for column_index in range(len(headers)):
            coordinate = (source_row_number, column_index + 1)
            if coordinate in merged_values and not clean_text(
                source_values[column_index]
                if column_index < len(source_values)
                else None
            ):
                if column_index >= len(source_values):
                    source_values.extend(
                        [None] * (column_index + 1 - len(source_values))
                    )
                source_values[column_index] = merged_values[coordinate]
                merged_flags = True
        if merged_flags:
            raw_rows[row_index] = source_values

        if not any(clean_text(value) for value in source_values[: len(headers)]):
            continue
        if len(rows) >= max_rows:
            warnings.append(_warning("ROW_LIMIT_REACHED", severity="error"))
            break

        raw_data = {
            header: _json_safe(
                source_values[index] if index < len(source_values) else None
            )
            for index, header in enumerate(headers)
        }
        row_warnings: list[dict[str, Any]] = []
        for column_index, header in enumerate(headers):
            coordinate = (source_row_number, column_index + 1)
            if coordinate in formula_cells and raw_data[header] is None:
                row_warnings.append(_warning("FORMULA_WITHOUT_CACHED_VALUE"))
        rows.append(
            ParsedRow(
                raw_data=raw_data,
                warnings=row_warnings,
                source_row_number=source_row_number,
            )
        )

    if not rows:
        warnings.append(_warning("SHEET_EMPTY"))

    _apply_currency(
        rows,
        final_mapping,
        document_currency=document_currency,
        default_currency=default_currency,
        warnings=warnings,
        used_headers=set(headers),
    )

    return ParsedDocument(
        file_type="xlsx",
        mapping=final_mapping,
        rows=rows,
        warnings=warnings,
        available_sheets=sheets,
        worksheet_name=worksheet_name,
    )


def _normalize_pdf_line(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped:
        return []
    parts = [part for part in re.split(r"\s{2,}", stripped) if part.strip()]
    if len(parts) == 1:
        return [normalize_pdf_cell(parts[0])]
    return [normalize_pdf_cell(part) for part in parts]


def _pdf_table_rows(page: Any) -> list[list[str]]:
    try:
        tables = page.extract_tables()
    except Exception:  # pragma: no cover - pdfplumber internals
        return []
    best: list[list[str]] = []
    for table in tables:
        rows = [
            [normalize_pdf_cell(cell) for cell in row] for row in table if row
        ]
        if len(rows) >= 2 and sum(len(row) for row in rows) > sum(
            len(row) for row in best
        ):
            best = rows
    return best


def _pdf_word_rows(page: Any) -> list[list[str]]:
    """Recover columns from word positions when text extraction yields one column.

    Words are grouped into visual lines by ``top`` with a small tolerance, then
    split into cells on gaps that are clearly wider than intra-cell spacing.
    """
    try:
        words = page.extract_words()
    except Exception:  # pragma: no cover - pdfplumber internals
        return []
    words = [word for word in words if clean_text(word.get("text"))][:5000]
    if not words:
        return []

    lines: list[dict[str, Any]] = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        placed = False
        for line in lines:
            if abs(line["top"] - word["top"]) <= 2.0:
                line["words"].append(word)
                placed = True
                break
        if not placed:
            lines.append({"top": word["top"], "words": [word]})

    result: list[list[str]] = []
    for line in sorted(lines, key=lambda item: item["top"]):
        line_words = sorted(line["words"], key=lambda item: item["x0"])
        heights = [
            word["height"] for word in line_words if word.get("height")
        ]
        average_height = sum(heights) / len(heights) if heights else 10.0
        tolerance = max(6.0, average_height * 0.6)
        cells: list[str] = []
        current = [line_words[0]["text"]]
        previous_x1 = line_words[0]["x1"]
        for word in line_words[1:]:
            gap = word["x0"] - previous_x1
            if gap > tolerance:
                cells.append(" ".join(current))
                current = [word["text"]]
            else:
                current.append(word["text"])
            previous_x1 = max(previous_x1, word["x1"])
        cells.append(" ".join(current))
        result.append([normalize_pdf_cell(cell) for cell in cells])
    return result


_SUMMARY_EN = frozenset({"total", "totals", "subtotal", "summary", "sum"})
_SUMMARY_AR_ENDINGS = ("جمالي", "جمالى", "احمالي", "احمالى", "مجموع")


def _is_summary_row(row: list[str]) -> bool:
    """True for totals/footer rows that must never become recipient rows.

    Arabic PDF text can arrive mirrored or with ligatures that break a plain
    ``الإجمالي`` match, so the Arabic check uses letter-unified stems.  English
    totals may also arrive reversed (``latoT``) in RTL cells.
    """
    values = [clean_text(value) for value in row if clean_text(value)]
    # A real data row can contain a surname ending in ``الجمالي``; a totals
    # row does not carry a phone number.  Requiring the absence of a phone
    # prevents dropping legitimate guardian/student names.
    has_phone = any(len(_digits(value)) >= 9 for value in values)
    for text in values:
        normalized = strip_arabic_marks(unify_arabic_letters(text)).strip(
            " .:،/|"
        )
        if not has_phone and normalized.endswith(_SUMMARY_AR_ENDINGS):
            return True
        for token in re.findall(r"[A-Za-z]+", text):
            lowered = token.casefold()
            if not has_phone and (
                lowered in _SUMMARY_EN or lowered[::-1] in _SUMMARY_EN
            ):
                return True
    return False


def _is_data_candidate(row: list[str]) -> bool:
    """Keep real tabular rows and drop titles, notes and totals."""
    values = [clean_text(value) for value in row if clean_text(value)]
    return len(values) >= 2 and not _is_summary_row(row)


def _looks_like_header_row(row: list[str]) -> bool:
    values = [clean_text(value) for value in row if clean_text(value)]
    if len(values) < 2:
        return False
    if any(_is_phone_value(value) for value in values):
        return False
    if any(len(_digits(value)) >= 9 for value in values):
        return False
    if any(_is_money_value(value) for value in values):
        return False
    money_values = sum(1 for value in values if _is_money_value(value))
    if money_values * 2 >= len(values):
        return False
    text_values = sum(1 for value in values if _has_letters(value))
    return text_values * 10 >= len(values) * 6


def _infer_pdf_layout(
    rows: list[list[str]],
    *,
    scan_limit: int,
    warnings: list[dict[str, Any]],
) -> _Layout | None:
    rows = [row for row in rows if any(clean_text(value) for value in row)]
    if not rows:
        return None

    found = _try_infer_header(rows, scan_limit=scan_limit)
    if found is None:
        if _looks_like_header_row(rows[0]):
            headers = _unique_headers(rows[0])
            data_rows = rows[1:]
            data_start = 1
        else:
            headers = _synthetic_headers(_max_width(rows))
            data_rows = rows
            data_start = 0
        data_rows = [row for row in data_rows if _is_data_candidate(row)]
        auto_mapping = _heuristic_mapping(data_rows, headers)
        _append_warning(warnings, "HEADER_NOT_FOUND")
        return _Layout(
            headers=headers,
            mapping=auto_mapping,
            data_start=data_start,
            heuristic=True,
            data_rows=data_rows,
        )

    header_index, headers, auto_mapping = found
    data_start = header_index + 1
    data_rows = [row for row in rows[data_start:] if _is_data_candidate(row)]
    if not _sufficient_mapping(auto_mapping):
        heuristic = _heuristic_mapping(data_rows, headers, auto_mapping)
        auto_mapping = {**heuristic, **auto_mapping}
        _append_warning(warnings, "HEADER_NOT_FOUND")
        return _Layout(
            headers=headers,
            mapping=auto_mapping,
            data_start=data_start,
            heuristic=True,
            data_rows=data_rows,
        )
    return _Layout(
        headers=headers,
        mapping=auto_mapping,
        data_start=data_start,
        heuristic=False,
        data_rows=data_rows,
    )


def _stage_layout_rows(
    layout: _Layout,
    *,
    page_number: int,
    mapping: dict[str, str] | None,
    resolved_mapping: dict[str, str],
    resolved_headers: list[str],
    rows: list[ParsedRow],
) -> tuple[dict[str, str], list[str]]:
    if not resolved_mapping:
        resolved_mapping = _merge_mapping(
            layout.headers, layout.mapping, mapping
        )
        resolved_headers = list(layout.headers)
    elif len(layout.headers) != len(resolved_headers):
        # A different page layout: keep this page's own headers.
        resolved_headers = list(layout.headers)

    page_rows = [
        row for row in (layout.data_rows or []) if _is_data_candidate(row)
    ]
    for values in page_rows:
        raw_data = {
            header: _json_safe(values[index] if index < len(values) else None)
            for index, header in enumerate(resolved_headers)
        }
        rows.append(
            ParsedRow(
                raw_data=raw_data,
                source_page_number=page_number,
            )
        )
    return resolved_mapping, resolved_headers


def parse_pdf(
    path: Path,
    *,
    mapping: dict[str, str] | None,
    max_pages: int,
    default_currency: str | None = None,
) -> ParsedDocument:
    warnings: list[dict[str, Any]] = []
    rows: list[ParsedRow] = []
    resolved_mapping: dict[str, str] = {}
    resolved_headers: list[str] = []
    document_currency: str | None = None
    scanned_pages_without_rows = 0
    ocr_pages_used = 0
    ocr_ready = settings.ocr_enabled and ocr_is_available()

    with pdfplumber.open(path) as document:
        pages = document.pages
        if len(pages) > max_pages:
            warnings.append(_warning("PAGE_LIMIT_REACHED", severity="error"))
            pages = pages[:max_pages]

        for page_number, page in enumerate(pages, start=1):
            text = page.extract_text() or ""
            # Image-only pages sometimes still return a bogus single-cell
            # "table" from pdfplumber.  Text presence, not table structure,
            # decides whether this page needs OCR.
            if len(text.strip()) < _PDF_TEXT_THRESHOLD:
                ocr_result = None
                if ocr_ready:
                    if ocr_pages_used >= settings.ocr_max_pages:
                        _append_warning(warnings, "OCR_PAGE_LIMIT")
                    else:
                        ocr_pages_used += 1
                        ocr_result = ocr_page(page)

                layout: _Layout | None = None
                if ocr_result is not None and ocr_result.rows:
                    if document_currency is None:
                        document_currency = detect_currency(ocr_result.text)
                    layout = _infer_pdf_layout(
                        ocr_result.rows,
                        scan_limit=_PDF_HEADER_SCAN_LIMIT,
                        warnings=warnings,
                    )
                    if layout is None or not any(
                        _is_data_candidate(row)
                        for row in (layout.data_rows or [])
                    ):
                        layout = None

                if layout is None:
                    scanned_pages_without_rows += 1
                    continue

                _append_warning(warnings, "OCR_USED")
                if (
                    ocr_result is not None
                    and ocr_result.mean_confidence
                    < settings.ocr_min_confidence
                ):
                    _append_warning(warnings, "LOW_CONFIDENCE_EXTRACTION")
                resolved_mapping, resolved_headers = _stage_layout_rows(
                    layout,
                    page_number=page_number,
                    mapping=mapping,
                    resolved_mapping=resolved_mapping,
                    resolved_headers=resolved_headers,
                    rows=rows,
                )
                continue

            table_rows = _pdf_table_rows(page)
            if document_currency is None:
                document_currency = detect_currency(text)

            layout = None
            used_text_fallback = False
            if table_rows:
                layout = _infer_pdf_layout(
                    table_rows,
                    scan_limit=_PDF_HEADER_SCAN_LIMIT,
                    warnings=warnings,
                )

            if layout is None:
                line_rows = [
                    _normalize_pdf_line(line)
                    for line in text.splitlines()
                    if line.strip()
                ]
                if not any(len(row) >= 2 for row in line_rows):
                    word_rows = _pdf_word_rows(page)
                    if any(len(row) >= 2 for row in word_rows):
                        line_rows = word_rows
                line_rows = [row for row in line_rows if len(row) >= 2]
                if line_rows:
                    layout = _infer_pdf_layout(
                        line_rows,
                        scan_limit=_HEADER_SCAN_LIMIT,
                        warnings=warnings,
                    )
                    used_text_fallback = layout is not None

            if layout is None:
                continue

            if document_currency is None:
                for header in layout.headers:
                    document_currency = detect_currency(header)
                    if document_currency is not None:
                        break

            resolved_mapping, resolved_headers = _stage_layout_rows(
                layout,
                page_number=page_number,
                mapping=mapping,
                resolved_mapping=resolved_mapping,
                resolved_headers=resolved_headers,
                rows=rows,
            )

            if used_text_fallback:
                _append_warning(warnings, "LOW_CONFIDENCE_EXTRACTION")

    if scanned_pages_without_rows:
        warnings.insert(0, _warning("SCANNED_PDF"))
    if not rows and not scanned_pages_without_rows:
        warnings.append(_warning("NO_EXTRACTABLE_TEXT"))

    _apply_currency(
        rows,
        resolved_mapping,
        document_currency=document_currency,
        default_currency=default_currency,
        warnings=warnings,
        used_headers=set(resolved_headers),
    )

    return ParsedDocument(
        file_type="pdf",
        mapping=resolved_mapping,
        rows=rows,
        warnings=warnings,
        available_sheets=None,
        worksheet_name=None,
    )
