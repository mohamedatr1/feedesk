from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from .constants import ALLOWED_VARIABLE_NAMES

_VARIABLE_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
_WHITESPACE = re.compile(r"\s+")

STUDENT_SEPARATOR = "، "


def format_amount(value: Decimal | str | int | None) -> str:
    """Format money deterministically with grouping and two decimals."""
    if value is None or value == "":
        return "0.00"
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"{amount:,.2f}"


def find_unknown_variables(body: str) -> list[str]:
    return sorted(
        {
            match.group(1)
            for match in _VARIABLE_PATTERN.finditer(body or "")
            if match.group(1) not in ALLOWED_VARIABLE_NAMES
        }
    )


def _clean_text(value: str | None) -> str:
    return _WHITESPACE.sub(" ", value or "").strip()


@dataclass(frozen=True)
class RenderResult:
    body: str
    unknown_variables: list[str] = field(default_factory=list)
    unresolved_variables: list[str] = field(default_factory=list)


def render_template(
    template_body: str,
    *,
    guardian_name: str | None,
    student_names: list[str] | None,
    amount: Decimal | str | int | None,
    currency: str | None,
    fee_periods: list[str] | None,
    school_name: str | None,
    school_contact: str | None,
) -> RenderResult:
    """Render an Arabic SMS body using only the documented variables.

    Unknown placeholders are kept verbatim and reported so approval can be
    blocked. Required variables that have no value are also kept verbatim.
    Output is plain text with repeated whitespace collapsed.
    """
    students = [name for name in (student_names or []) if _clean_text(name)]
    periods = [period for period in (fee_periods or []) if _clean_text(period)]
    resolved_guardian = _clean_text(guardian_name)
    resolved_currency = _clean_text(currency)
    resolved_amount = format_amount(amount) if amount is not None else ""

    values: dict[str, str | None] = {
        "guardian_name": resolved_guardian or None,
        "school_name": _clean_text(school_name) or "المدرسة",
        "student_name": _clean_text(students[0]) if students else "الطالب",
        "student_list": STUDENT_SEPARATOR.join(_clean_text(name) for name in students)
        or "أبنائكم",
        "amount": resolved_amount or None,
        "currency": resolved_currency or None,
        "fee_period": STUDENT_SEPARATOR.join(_clean_text(period) for period in periods)
        or "الفصل الحالي",
        "school_contact": _clean_text(school_contact) or "إدارة المدرسة",
    }

    unresolved: set[str] = set()
    unknown = set(find_unknown_variables(template_body))

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in unknown:
            unresolved.add(name)
            return match.group(0)
        value = values.get(name)
        if value is None or value == "":
            unresolved.add(name)
            return match.group(0)
        return value

    rendered = _VARIABLE_PATTERN.sub(replace, template_body or "")
    rendered = _WHITESPACE.sub(" ", rendered).strip()
    return RenderResult(
        body=rendered,
        unknown_variables=sorted(unknown),
        unresolved_variables=sorted(unresolved),
    )
