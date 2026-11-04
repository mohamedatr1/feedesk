"""Generate synthetic XLSX import-acceptance fixtures for FeeDesk.

Every value in this file is fabricated.  No real guardian, student, phone or
payment data is used.  The fixtures intentionally exercise the parser's
layout, header, currency, digit and validation heuristics.

Usage:
    python scripts/qa_fixtures/generate_xlsx.py
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / ".local" / "samples" / "qa"

# ---------------------------------------------------------------------------
# Shared styling helpers
# ---------------------------------------------------------------------------

NAVY = "1F3864"
TEAL = "0F6B78"
LIGHT = "EAF1F8"
AMBER = "FFF2CC"
GREY = "F2F2F2"
WHITE = "FFFFFF"

THIN = Side(style="thin", color="B7C4D6")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

ARABIC_FONT = "Tahoma"
LATIN_FONT = "Calibri"


def _rtl_alignment(horizontal: str = "right") -> Alignment:
    return Alignment(horizontal=horizontal, vertical="center", readingOrder=2, wrap_text=True)


def _ltr_alignment(horizontal: str = "left") -> Alignment:
    return Alignment(horizontal=horizontal, vertical="center", wrap_text=True)


def _title(
    ws,
    row: int,
    text: str,
    last_col: int,
    *,
    rtl: bool,
    size: int = 16,
    fill: str | None = None,
) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = Font(name=ARABIC_FONT if rtl else LATIN_FONT, size=size, bold=True, color=NAVY)
    cell.alignment = _rtl_alignment("center" if rtl else "left") if rtl else Alignment(
        horizontal="left", vertical="center", wrap_text=True
    )
    if fill:
        cell.fill = PatternFill("solid", fgColor=fill)
    ws.row_dimensions[row].height = max(24, size + 12)


def _subtitle(ws, row: int, text: str, last_col: int, *, rtl: bool) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = Font(name=ARABIC_FONT if rtl else LATIN_FONT, size=10, italic=True, color="44546A")
    cell.alignment = _rtl_alignment() if rtl else Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[row].height = 20


def _header_row(ws, row: int, headers: list[str], *, rtl: bool) -> None:
    for index, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=index, value=header)
        cell.font = Font(name=ARABIC_FONT if rtl else LATIN_FONT, size=10, bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=TEAL)
        cell.alignment = _rtl_alignment("center") if rtl else Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        cell.border = BORDER
    ws.row_dimensions[row].height = 30


def _data_row(ws, row: int, values: list[Any], *, rtl: bool, shade: bool = False) -> None:
    for index, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=index, value=value)
        cell.font = Font(name=ARABIC_FONT if rtl else LATIN_FONT, size=10)
        cell.border = BORDER
        cell.alignment = _rtl_alignment() if rtl else _ltr_alignment()
        if shade:
            cell.fill = PatternFill("solid", fgColor=GREY)
        if isinstance(value, (int, float)):
            cell.number_format = "#,##0.00"
    ws.row_dimensions[row].height = 22


def _footer_row(ws, row: int, label: str, values: dict[int, Any], *, rtl: bool) -> None:
    for column, value in values.items():
        cell = ws.cell(row=row, column=column, value=value)
        cell.font = Font(name=ARABIC_FONT if rtl else LATIN_FONT, size=10, bold=True, color=NAVY)
        cell.fill = PatternFill("solid", fgColor=LIGHT)
        cell.border = BORDER
        cell.alignment = _rtl_alignment() if rtl else _ltr_alignment()
        if isinstance(value, (int, float)):
            cell.number_format = "#,##0.00"
    label_cell = ws.cell(row=row, column=1, value=label)
    label_cell.font = Font(name=ARABIC_FONT if rtl else LATIN_FONT, size=10, bold=True, color=NAVY)
    label_cell.fill = PatternFill("solid", fgColor=LIGHT)
    label_cell.border = BORDER
    label_cell.alignment = _rtl_alignment() if rtl else _ltr_alignment()
    ws.row_dimensions[row].height = 24


def _widths(ws, widths: list[float]) -> None:
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(index)].width = width


def _new_sheet(wb: Workbook, title: str, *, rtl: bool):
    ws = wb.create_sheet(title)
    ws.sheet_view.rightToLeft = rtl
    ws.sheet_view.showGridLines = True
    return ws


def _save(wb: Workbook, filename: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    wb.save(path)
    return path


def _inject_cached_values(path: Path, sheet_index: int, cached: dict[str, Any]) -> None:
    """Add cached <v> results to formula cells that openpyxl writes bare.

    openpyxl intentionally does not calculate formulas.  Import parsers read
    workbooks with ``data_only=True``, so a fixture that proves cached-value
    support needs the value stored in the sheet XML.
    """

    with zipfile.ZipFile(path, "r") as source:
        entries = {name: source.read(name) for name in source.namelist()}

    target = f"xl/worksheets/sheet{sheet_index}.xml"
    xml = entries[target].decode("utf-8")

    for reference, value in cached.items():
        pattern = re.compile(
            rf'(<c r="{reference}"(?:\s[^>]*)?>)(.*?)(</c>)',
            re.DOTALL,
        )

        def replace(match: re.Match[str]) -> str:
            inner = match.group(2)
            if "<f" not in inner:
                raise RuntimeError(f"No formula found in cell {reference}")
            inner = re.sub(r"<v>.*?</v>", "", inner, flags=re.DOTALL)
            rendered = str(value)
            if isinstance(value, bool):
                rendered = "1" if value else "0"
            inner = inner.replace("</f>", f"</f><v>{rendered}</v>", 1)
            return match.group(1) + inner + match.group(3)

        xml, count = pattern.subn(replace, xml, count=1)
        if count != 1:
            raise RuntimeError(f"Could not patch cached value for {reference}")

    entries[target] = xml.encode("utf-8")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as target_zip:
        for name, data in entries.items():
            target_zip.writestr(name, data)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def build_x01_standard_ar_multisheet() -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    ws = _new_sheet(wb, "كشف الأقساط", rtl=True)
    _title(ws, 1, "QA-X01 — مدرسة الياسمين النموذجية", 6, rtl=True)
    _subtitle(ws, 2, "كشف أقساط الفصل الدراسي الأول 2026/2027 — نسخة تجريبية اصطناعية", 6, rtl=True)
    headers = ["اسم الطالب", "اسم ولي الأمر", "رقم الهاتف", "المتبقي", "العملة", "الفصل"]
    _header_row(ws, 3, headers, rtl=True)
    rows = [
        ["ريم القاسم", "أحمد القاسم", "+963 944 110 101", 1250000, "SYP", "الفصل الأول"],
        ["عمر الحمصي", "سامية الحمصي", "+963 944 110 102", 980000, "SYP", "الفصل الأول"],
        ["سلمى النعيمي", "خالد النعيمي", "+963 944 110 103", 1475000, "SYP", "الفصل الأول"],
        ["خالد الشامي", "منى الشامي", "+963 944 110 104", 760000, "SYP", "الفصل الأول"],
        ["نورا العلي", "فادي العلي", "+963 944 110 105", 2100000, "SYP", "الفصل الأول"],
        ["بشار الحلبي", "رنا الحلبي", "+963 944 110 106", 540000, "SYP", "الفصل الأول"],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 4 + offset, values, rtl=True, shade=offset % 2 == 1)
    _widths(ws, [20, 24, 20, 18, 12, 16])
    ws.freeze_panes = "A4"

    contacts = _new_sheet(wb, "أولياء الأمور", rtl=True)
    _title(contacts, 1, "دليل أولياء الأمور — بيانات اصطناعية", 4, rtl=True)
    _header_row(contacts, 3, ["اسم ولي الأمر", "رقم الهاتف", "عدد الطلاب", "ملاحظة"], rtl=True)
    for offset, values in enumerate(
        [
            ["أحمد القاسم", "+963 944 110 101", 1, "ولي أمر"],
            ["سامية الحمصي", "+963 944 110 102", 1, "ولي أمر"],
            ["خالد النعيمي", "+963 944 110 103", 1, "ولي أمر"],
            ["منى الشامي", "+963 944 110 104", 1, "ولي أمر"],
            ["فادي العلي", "+963 944 110 105", 1, "ولي أمر"],
            ["رنا الحلبي", "+963 944 110 106", 1, "ولي أمر"],
        ]
    ):
        _data_row(contacts, 4 + offset, values, rtl=True)
    _widths(contacts, [24, 20, 12, 18])

    notes = _new_sheet(wb, "ملاحظات", rtl=True)
    _title(notes, 1, "ملاحظات الكشف", 2, rtl=True)
    notes["A3"] = "هذه بيانات تجريبية بالكامل، أسماء وهواتف ومبالغ اصطناعية."
    notes["A4"] = "لا يوجد أي اتصال بالشبكة ولا أي بيانات شخصية حقيقية."
    notes["A5"] = "العملة الافتراضية للكشف: الليرة السورية."
    for row in range(3, 6):
        notes.cell(row=row, column=1).font = Font(name=ARABIC_FONT, size=10)
        notes.cell(row=row, column=1).alignment = _rtl_alignment()
    _widths(notes, [80, 20])
    return _save(wb, "xlsx-01-standard-ar-multisheet.xlsx")


def build_x02_standard_en_headers() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Statement"
    _title(ws, 1, "QA-X02 — Al-Noor International School", 6, rtl=False)
    _subtitle(ws, 2, "Synthetic import acceptance fixture — English headers, USD", 6, rtl=False)
    _header_row(
        ws,
        3,
        ["Guardian Name", "Phone Number", "Student Name", "Remaining Balance", "Currency", "Term"],
        rtl=False,
    )
    rows = [
        ["Maya Haddad", "+963 933 120 201", "Leen Haddad", 420.00, "USD", "Fall 2026"],
        ["Omar Nassar", "+963 933 120 202", "Yara Nassar", 315.50, "USD", "Fall 2026"],
        ["Lina Farah", "+963 933 120 203", "Karim Farah", 780.00, "USD", "Fall 2026"],
        ["Ziad Mansour", "+963 933 120 204", "Dana Mansour", 250.00, "USD", "Fall 2026"],
        ["Rana Kassem", "+963 933 120 205", "Sami Kassem", 610.75, "USD", "Fall 2026"],
        ["Tarek Aziz", "+963 933 120 206", "Nour Aziz", 190.00, "USD", "Fall 2026"],
        ["Dima Rizk", "+963 933 120 207", "Elie Rizk", 845.25, "USD", "Fall 2026"],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 4 + offset, values, rtl=False, shade=offset % 2 == 1)
    _widths(ws, [24, 20, 22, 20, 12, 14])
    ws.freeze_panes = "A4"
    return _save(wb, "xlsx-02-standard-en-headers.xlsx")


def build_x03_mixed_extra_columns() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف مختلط"
    ws.sheet_view.rightToLeft = True
    _title(ws, 1, "QA-X03 — كشف مختلط المصادر والأعمدة الإضافية", 9, rtl=True)
    headers = [
        "Ref",
        "اسم ولي الأمر",
        "Phone",
        "Student Name",
        "المتبقي",
        "Currency",
        "ملاحظات",
        "حالة القيد",
        "عمود فارغ",
    ]
    _header_row(ws, 2, headers, rtl=True)
    rows = [
        ["R-3001", "هيثم درويش", "+963 988 130 301", "ليان درويش", 640000, "SYP", "قيد الانتظام", "نشط", None],
        ["R-3002", "غادة مرعي", "+963 988 130 302", "جواد مرعي", 0, "SYP", "متابعة هاتفية", "نشط", None],
        ["R-3003", "أنس شعبان", "+963 988 130 301", "ريتا شعبان", 890000, "SYP", "هاتف مشترك مع ولي أمر آخر", "نشط", None],
        ["R-3004", "ريما خوري", "+963 988 130 304", "ميشيل خوري", 1150000, "SYP", "قسط أول", "نشط", None],
        ["R-3005", "وليد سلوم", "+963 988 130 305", "لينا سلوم", 530000, "SYP", "قسط ثانٍ", "نشط", None],
        ["R-3006", "ميرا جبور", "+963 988 130 306", "أنطون جبور", 725000, "SYP", "قسط ثالث", "نشط", None],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 3 + offset, values, rtl=True, shade=offset % 2 == 1)
    _widths(ws, [10, 22, 20, 22, 16, 10, 28, 12, 12])
    return _save(wb, "xlsx-03-mixed-headers-extra-columns.xlsx")


def build_x04_header_row_seven() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف الأقساط"
    ws.sheet_view.rightToLeft = True
    _title(ws, 1, "QA-X04 — مدرسة الأمل الخاصة", 6, rtl=True)
    _subtitle(ws, 2, "كشف أقساط الفصل الثاني — نسخة تجريبية", 6, rtl=True)
    ws.merge_cells("A3:F3")
    ws["A3"] = "ملاحظة: صف الترويسة الفعلي يقع في الصف السابع، وتوجد صفوف عنوان وملاحظات أعلاه."
    ws["A3"].font = Font(name=ARABIC_FONT, size=10, color="7F6000")
    ws["A3"].fill = PatternFill("solid", fgColor=AMBER)
    ws["A3"].alignment = _rtl_alignment()
    ws.row_dimensions[3].height = 34
    ws.merge_cells("A4:F4")
    ws["A4"] = "رقم الملف: QA-X04 | تاريخ إصدار اصطناعي: 2026-10-01 | العملة: SYP"
    ws["A4"].font = Font(name=ARABIC_FONT, size=10)
    ws["A4"].alignment = _rtl_alignment()
    ws["A6"] = "بيانات الكشف"
    ws["A6"].font = Font(name=ARABIC_FONT, size=12, bold=True, color=NAVY)
    ws["A6"].alignment = _rtl_alignment()
    headers = ["اسم ولي الأمر", "رقم الهاتف", "اسم الطالب", "المتبقي", "العملة", "الفصل"]
    _header_row(ws, 7, headers, rtl=True)
    rows = [
        ["سمير عيد", "+963 999 140 401", "رامي عيد", 1330000, "SYP", "الفصل الثاني"],
        ["هالة صباغ", "+963 999 140 402", "لارا صباغ", 870000, "SYP", "الفصل الثاني"],
        ["مازن قطان", "+963 999 140 403", "هاني قطان", 1560000, "SYP", "الفصل الثاني"],
        ["روان حجو", "+963 999 140 404", "ميرا حجو", 495000, "SYP", "الفصل الثاني"],
        ["نبيل زين", "+963 999 140 405", "زياد زين", 1025000, "SYP", "الفصل الثاني"],
        ["جنى عوض", "+963 999 140 406", "كريم عوض", 680000, "SYP", "الفصل الثاني"],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 8 + offset, values, rtl=True, shade=offset % 2 == 1)
    _widths(ws, [24, 20, 22, 16, 10, 16])
    return _save(wb, "xlsx-04-header-at-row-7.xlsx")


def build_x05_headerless_three_columns() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف بلا ترويسة"
    ws.sheet_view.rightToLeft = True
    ws.merge_cells("A1:C1")
    ws["A1"] = "QA-X05 — مدرسة الندى — كشف أقساط الصف السادس"
    ws["A1"].font = Font(name=ARABIC_FONT, size=15, bold=True, color=NAVY)
    ws["A1"].alignment = _rtl_alignment("center")
    ws.row_dimensions[1].height = 28
    ws.merge_cells("A2:C2")
    ws["A2"] = "ملف بلا صف ترويسة: ثلاث أعمدة فقط (الاسم، الهاتف، المبلغ). العملة من إعدادات المدرسة."
    ws["A2"].font = Font(name=ARABIC_FONT, size=10, italic=True, color="44546A")
    ws["A2"].alignment = _rtl_alignment()
    rows = [
        ["فؤاد جمال", "+963 944 150 501", 720000],
        ["عبير حمدان", "+963 944 150 502", 485000],
        ["سامي عيسى", "+963 944 150 503", 1340000],
        ["لينا بركات", "+963 944 150 504", 960000],
        ["مخلص دياب", "+963 944 150 505", 615000],
        ["هند علوش", "+963 944 150 506", 1080000],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 4 + offset, values, rtl=True, shade=offset % 2 == 1)
    _widths(ws, [24, 20, 18])
    return _save(wb, "xlsx-05-headerless-3col-school-currency.xlsx")


def build_x06_headerless_five_columns() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف خماسي"
    ws.sheet_view.rightToLeft = True
    ws.merge_cells("A1:E1")
    ws["A1"] = "QA-X06 — مدرسة الرافدين — كشف أقساط بلا ترويسة"
    ws["A1"].font = Font(name=ARABIC_FONT, size=15, bold=True, color=NAVY)
    ws["A1"].alignment = _rtl_alignment("center")
    rows = [
        ["غسان خليل", "+963 933 160 601", 540000, "SYP", "ريم خليل"],
        ["إيمان سليمان", "+963 933 160 602", 0, "SYP", "حسام سليمان"],
        ["رامي عبدو", "+963 933 160 603", 1275000, "SYP", "نايا عبدو"],
        ["سارة ملحم", "+963 933 160 604", 890000, "SYP", "جورج ملحم"],
        ["كرم حنا", "+963 933 160 605", 430000, "SYP", "سلوى حنا"],
        ["دانية ناصر", "+963 933 160 606", 1650000, "SYP", "فارس ناصر"],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 3 + offset, values, rtl=True, shade=offset % 2 == 1)
    _widths(ws, [24, 20, 18, 10, 22])
    return _save(wb, "xlsx-06-headerless-5col.xlsx")


def build_x07_merged_headers_guardians() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف الأقساط"
    ws.sheet_view.rightToLeft = True
    _title(ws, 1, "QA-X07 — مدرسة مار يوسف — ترويسة وخلايا ولي أمر مدمجة", 6, rtl=True)

    # Two merged header groups (values live only in the top-left cell).
    ws.merge_cells("A2:B2")
    ws["A2"] = "بيانات الطالب"
    ws.merge_cells("C2:D2")
    ws["C2"] = "بيانات ولي الأمر"
    ws.merge_cells("E2:F2")
    ws["E2"] = "بيانات القسط"
    for cell_ref in ("A2", "C2", "E2"):
        ws[cell_ref].font = Font(name=ARABIC_FONT, size=10, bold=True, color=WHITE)
        ws[cell_ref].fill = PatternFill("solid", fgColor=NAVY)
        ws[cell_ref].alignment = _rtl_alignment("center")
        ws[cell_ref].border = BORDER

    _header_row(ws, 3, ["اسم الطالب", "الصف", "اسم ولي الأمر", "رقم الهاتف", "المتبقي", "العملة"], rtl=True)

    rows = [
        ["ليان سامر الحلبي", "الصف الخامس", "سامر الحلبي", "+963 988 170 701", 1250000, "SYP"],
        ["آدم سامر الحلبي", "الصف الثالث", None, None, 980000, "SYP"],
        ["جودي فادي مارون", "الصف الرابع", "فادي مارون", "+963 999 170 703", 760000, "SYP"],
        ["ماريا فادي مارون", "الصف الثاني", None, None, 640000, "SYP"],
        ["زين نورا عبد الرحمن", "الصف السادس", "نورا عبد الرحمن", "+963 944 170 705", 1450000, "SYP"],
        ["لين نورا عبد الرحمن", "الصف الأول", None, None, 520000, "SYP"],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 4 + offset, values, rtl=True, shade=offset % 2 == 1)

    # Sibling rows share a guardian name and phone through merged cells.
    ws.merge_cells("C4:C5")
    ws.merge_cells("D4:D5")
    ws.merge_cells("C6:C7")
    ws.merge_cells("D6:D7")
    ws.merge_cells("C8:C9")
    ws.merge_cells("D8:D9")
    _widths(ws, [26, 16, 24, 20, 16, 10])
    return _save(wb, "xlsx-07-merged-headers-guardians.xlsx")


def build_x08_arabic_indic_digits() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف الأرقام العربية"
    ws.sheet_view.rightToLeft = True
    _title(ws, 1, "QA-X08 — مدرسة دمشق النموذجية — أرقام عربية وفواصل عشرية (ل.س)", 4, rtl=True)
    _header_row(ws, 2, ["اسم الطالب", "اسم ولي الأمر", "رقم الهاتف", "المتبقي"], rtl=True)
    rows = [
        ["أحمد الغزي", "محمود الغزي", "+٩٦٣ ٩٤٤ ١٨٠ ٨٠١", "١٬٢٥٠٬٠٠٠ ل.س"],
        ["فاطمة الشعار", "عدنان الشعار", "+٩٦٣ ٩٤٤ ١٨٠ ٨٠٢", "٨٧٥٬٥٠٠٫٥٠ ل.س"],
        ["يوسف الحاج", "سميرة الحاج", "+٩٦٣ ٩٤٤ ١٨٠ ٨٠٣", "١٬٤٤٠٬٢٥٠٫٧٥ ل.س"],
        ["مريم العبود", "ناصر العبود", "+٩٦٣ ٩٤٤ ١٨٠ ٨٠٤", "٦٣٠٬٠٠٠ ل.س"],
        ["حسين الرفاعي", "هناء الرفاعي", "+٩٦٣ ٩٤٤ ١٨٠ ٨٠٥", "٢٬١٠٠٬٠٠٠٫٠٠ ل.س"],
        ["سعاد القاضي", "فوزي القاضي", "+٩٦٣ ٩٤٤ ١٨٠ ٨٠٦", "٥٤٥٬٧٥٠٫٢٥ ل.س"],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 3 + offset, values, rtl=True, shade=offset % 2 == 1)
    _widths(ws, [22, 24, 22, 22])
    return _save(wb, "xlsx-08-arabic-indic-digits-lira.xlsx")


def build_x09_multi_currency() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف متعدد العملات"
    ws.sheet_view.rightToLeft = True
    _title(ws, 1, "QA-X09 — مدرسة العالمية — كشف بعملتين SYP و USD", 4, rtl=True)
    _subtitle(ws, 2, "صفوف بالليرة السورية وأخرى بالدولار الأمريكي عبر عمود العملة", 4, rtl=True)
    _header_row(ws, 3, ["اسم ولي الأمر", "رقم الهاتف", "اسم الطالب", "المتبقي", "العملة"], rtl=True)
    rows = [
        ["جورج حداد", "+963 933 190 901", "ريك حداد", 1250000, "SYP"],
        ["أمل الشيخ", "+963 933 190 902", "ليان الشيخ", 420.50, "USD"],
        ["باسل عدرا", "+963 933 190 903", "مروان عدرا", 780000, "SYP"],
        ["ديما زريق", "+963 933 190 904", "سيرين زريق", 315.75, "USD"],
        ["عماد الحسن", "+963 933 190 905", "هيثم الحسن", 1640000, "SYP"],
        ["ليلى فرحات", "+963 933 190 906", "جاد فرحات", 260.00, "USD"],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 4 + offset, values, rtl=True, shade=offset % 2 == 1)
    _widths(ws, [24, 20, 22, 18, 10])
    return _save(wb, "xlsx-09-multi-currency-syp-usd.xlsx")


def build_x10_no_currency_column_usd_title() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف بالدولار"
    ws.sheet_view.rightToLeft = True
    ws.merge_cells("A1:D1")
    ws["A1"] = "QA-X10 — مدرسة النور الدولية — كشف الأقساط بالدولار الأمريكي (USD)"
    ws["A1"].font = Font(name=ARABIC_FONT, size=15, bold=True, color=NAVY)
    ws["A1"].alignment = _rtl_alignment("center")
    ws.row_dimensions[1].height = 28
    ws.merge_cells("A2:D2")
    ws["A2"] = "لا يوجد عمود عملة؛ العملة مستخرجة من عنوان الكشف (دولار / USD)."
    ws["A2"].font = Font(name=ARABIC_FONT, size=10, italic=True, color="44546A")
    ws["A2"].alignment = _rtl_alignment()
    _header_row(ws, 4, ["اسم ولي الأمر", "رقم الهاتف", "اسم الطالب", "المتبقي"], rtl=True)
    rows = [
        ["رند الجابي", "+963 988 200 101", "تالا الجابي", 520.00],
        ["شادي حبيب", "+963 988 200 102", "جو حبيب", 310.50],
        ["غالية سعادة", "+963 988 200 103", "ريم سعادة", 875.00],
        ["مروان عكاش", "+963 988 200 104", "سامر عكاش", 240.25],
        ["نادين شلهوب", "+963 988 200 105", "كرم شلهوب", 660.00],
        ["فارس معروف", "+963 988 200 106", "لينا معروف", 1090.75],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 5 + offset, values, rtl=True, shade=offset % 2 == 1)
    _widths(ws, [24, 20, 22, 18])
    return _save(wb, "xlsx-10-no-currency-col-usd-title.xlsx")


def build_x11_shuffled_columns() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف مبعثر"
    ws.sheet_view.rightToLeft = True
    _title(ws, 1, "QA-X11 — مدرسة الترتيب — أعمدة مبعثرة (الهاتف أولًا والأسماء أخيرًا)", 8, rtl=True)
    headers = [
        "Phone",
        "Remaining Balance",
        "Notes",
        "Currency",
        "Total Fee",
        "Student Name",
        "Amount Paid",
        "Guardian Name",
    ]
    _header_row(ws, 3, headers, rtl=True)
    rows = [
        ["+963 999 210 201", 500000, "قسط أول", "SYP", 900000, "ليان الحموي", 400000, "إياد الحموي"],
        ["+963 999 210 202", 275000, "قسط ثانٍ", "SYP", 800000, "سامر عبيد", 525000, "سوسن عبيد"],
        ["+963 999 210 203", 640000, "متابعة", "SYP", 1200000, "رهف الرفاعي", 560000, "طلال الرفاعي"],
        ["+963 999 210 204", 125000, "قسط ثالث", "SYP", 950000, "جو شماس", 825000, "رغد شماس"],
        ["+963 999 210 205", 980000, "قسط رابع", "SYP", 1500000, "ميرا درويش", 520000, "منال درويش"],
        ["+963 999 210 206", 410000, "قسط خامس", "SYP", 1100000, "زياد الحاج", 690000, "عدنان الحاج"],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 4 + offset, values, rtl=True, shade=offset % 2 == 1)
    _widths(ws, [20, 18, 18, 10, 16, 22, 16, 24])
    return _save(wb, "xlsx-11-shuffled-column-order.xlsx")


def build_x12_cover_before_statement() -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    cover = _new_sheet(wb, "الغلاف", rtl=True)
    _title(cover, 1, "QA-X12 — مدرسة السلام الأهلية", 3, rtl=True, size=20)
    cover["A3"] = "كشف أقساط تجريبي — الاصطناعي بالكامل"
    cover["A4"] = "رقم الملف: QA-X12"
    cover["A5"] = "التاريخ: 2026-10-15"
    cover["A6"] = "العملة: الليرة السورية (SYP)"
    for row in range(3, 7):
        cover.cell(row=row, column=1).font = Font(name=ARABIC_FONT, size=11)
        cover.cell(row=row, column=1).alignment = _rtl_alignment()
    _widths(cover, [60, 20, 20])

    notes = _new_sheet(wb, "ملاحظات", rtl=True)
    _title(notes, 1, "ملاحظات قبل الكشف", 2, rtl=True)
    notes["A3"] = "ورقة الغلاف والملاحظات تأتي قبل ورقة الكشف في ترتيب المصنف."
    notes["A4"] = "على المستورد اختيار ورقة الكشف تلقائيًا أو طلب اختيارها."
    notes["A5"] = "جميع الأسماء والهواتف والمبالغ مولّدة للاختبار فقط."
    for row in range(3, 6):
        notes.cell(row=row, column=1).font = Font(name=ARABIC_FONT, size=10)
        notes.cell(row=row, column=1).alignment = _rtl_alignment()
    _widths(notes, [80, 20])

    ws = _new_sheet(wb, "كشف الأقساط", rtl=True)
    _title(ws, 1, "كشف أقساط الفصل الأول — مدرسة السلام", 6, rtl=True)
    _header_row(ws, 3, ["اسم ولي الأمر", "رقم الهاتف", "اسم الطالب", "المتبقي", "العملة", "الفصل"], rtl=True)
    rows = [
        ["عصام الخطيب", "+963 944 220 301", "نور الخطيب", 1750000, "SYP", "الفصل الأول"],
        ["هبة نصر", "+963 944 220 302", "جاد نصر", 840000, "SYP", "الفصل الأول"],
        ["زياد الريس", "+963 944 220 303", "ليلى الريس", 1260000, "SYP", "الفصل الأول"],
        ["ندى حرب", "+963 944 220 304", "مروان حرب", 690000, "SYP", "الفصل الأول"],
        ["سليم قاسم", "+963 944 220 305", "رهف قاسم", 1450000, "SYP", "الفصل الأول"],
        ["أروى سلطان", "+963 944 220 306", "باسل سلطان", 580000, "SYP", "الفصل الأول"],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 4 + offset, values, rtl=True, shade=offset % 2 == 1)
    _widths(ws, [24, 20, 22, 18, 10, 16])
    return _save(wb, "xlsx-12-cover-before-statement.xlsx")


def build_x13_wide_empty_footer() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف عريض"
    ws.sheet_view.rightToLeft = True
    _title(ws, 1, "QA-X13 — مدرسة الرسم البياني — أعمدة وصفوف فارغة وصف إجمالي", 14, rtl=True)
    ws.merge_cells("A2:N2")
    ws["A2"] = "توجد أعمدة فارغة بين البيانات، وصفوف فارغة قبل صف الإجمالي في الأسفل."
    ws["A2"].font = Font(name=ARABIC_FONT, size=10, italic=True, color="44546A")
    ws["A2"].alignment = _rtl_alignment()

    header_map = {
        1: "اسم ولي الأمر",
        3: "رقم الهاتف",
        5: "اسم الطالب",
        7: "المتبقي",
        9: "العملة",
        11: "الفصل",
        13: "ملاحظات",
    }
    for column, header in header_map.items():
        cell = ws.cell(row=4, column=column, value=header)
        cell.font = Font(name=ARABIC_FONT, size=10, bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=TEAL)
        cell.alignment = _rtl_alignment("center")
        cell.border = BORDER
    ws.row_dimensions[4].height = 30

    rows = [
        ["مازن الخوري", "+963 933 230 401", "ريتا الخوري", 1150000, "SYP", "الفصل الأول", "منتظم"],
        ["ريما قنواتي", "+963 933 230 402", "جاد قنواتي", 830000, "SYP", "الفصل الأول", "منتظم"],
        ["سائد حمدي", "+963 933 230 403", "ليان حمدي", 1475000, "SYP", "الفصل الأول", "منتظم"],
        ["لمى عيسى", "+963 933 230 404", "مروان عيسى", 620000, "SYP", "الفصل الأول", "منتظم"],
        ["جابر الشامي", "+963 933 230 405", "هالة الشامي", 990000, "SYP", "الفصل الأول", "منتظم"],
        ["سناء مراد", "+963 933 230 406", "كرم مراد", 1340000, "SYP", "الفصل الأول", "منتظم"],
    ]
    for offset, values in enumerate(rows):
        row_number = 5 + offset
        for column, value in zip((1, 3, 5, 7, 9, 11, 13), values):
            cell = ws.cell(row=row_number, column=column, value=value)
            cell.font = Font(name=ARABIC_FONT, size=10)
            cell.border = BORDER
            cell.alignment = _rtl_alignment()
            if isinstance(value, (int, float)):
                cell.number_format = "#,##0.00"
        ws.row_dimensions[row_number].height = 22

    # Deliberately empty rows before the totals/footer row.
    total = sum(row[3] for row in rows)
    footer_values = {1: "الإجمالي", 7: total, 9: "SYP", 13: "صف إجمالي/تذييل"}
    _footer_row(ws, 13, "الإجمالي", footer_values, rtl=True)
    _widths(ws, [24, 4, 20, 4, 22, 4, 18, 4, 10, 4, 16, 4, 26, 4])
    return _save(wb, "xlsx-13-wide-empty-cols-footer.xlsx")


def build_x14_formulas_cached() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف بالمعادلات"
    ws.sheet_view.rightToLeft = True
    _title(ws, 1, "QA-X14 — مدرسة الحساب — معادلات بقيم مخزنة وأخرى بلا قيمة مخزنة", 7, rtl=True)
    _header_row(
        ws,
        3,
        ["اسم ولي الأمر", "رقم الهاتف", "اسم الطالب", "إجمالي القسط", "المدفوع", "المتبقي", "العملة"],
        rtl=True,
    )
    rows = [
        ["نبيل حداد", "+963 988 240 501", "لينا حداد", 1200000, 450000],
        ["غادة سمعان", "+963 988 240 502", "جو سمعان", 950000, 300000],
        ["رامي حبيب", "+963 988 240 503", "ميرا حبيب", 1450000, 700000],
        ["هيا صالح", "+963 988 240 504", "سامر صالح", 800000, 250000],
        ["مازن عبيد", "+963 988 240 505", "رهف عبيد", 1650000, 900000],
        ["رويدا جمال", "+963 988 240 506", "كريم جمال", 900000, 100000],
    ]
    for offset, (guardian, phone, student, total, paid) in enumerate(rows):
        row_number = 4 + offset
        _data_row(
            ws,
            row_number,
            [guardian, phone, student, total, paid, f"=D{row_number}-E{row_number}", "SYP"],
            rtl=True,
            shade=offset % 2 == 1,
        )

    path = _save(wb, "xlsx-14-formulas-cached-values.xlsx")

    # The last row intentionally has no cached result.  The parser must report
    # FORMULA_WITHOUT_CACHED_VALUE for it instead of inventing a balance.
    cached = {
        "F4": 750000,
        "F5": 650000,
        "F6": 750000,
        "F7": 550000,
        "F8": 750000,
    }
    _inject_cached_values(path, 1, cached)
    return path


def build_x15_invalid_values() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "كشف تحقق"
    ws.sheet_view.rightToLeft = True
    _title(ws, 1, "QA-X15 — كشف اختبارات التحقق: صفر، سالب، مكرر، هاتف مشترك ومفقود", 5, rtl=True)
    ws.merge_cells("A2:E2")
    ws["A2"] = "صفوف مقصودة لاختبار ZERO_BALANCE وNEGATIVE_BALANCE وDUPLICATE_ROW وSHARED_PHONE وMISSING_PHONE وINVALID_PHONE."
    ws["A2"].font = Font(name=ARABIC_FONT, size=10, italic=True, color="44546A")
    ws["A2"].alignment = _rtl_alignment()
    _header_row(ws, 4, ["اسم ولي الأمر", "رقم الهاتف", "اسم الطالب", "المتبقي", "العملة"], rtl=True)
    rows = [
        ["علاء الدين", "+963 999 250 601", "ليان علاء الدين", 750000, "SYP"],
        ["رهف الحمصي", "+963 999 250 602", "سامر الحمصي", 0, "SYP"],
        ["جواد سليمان", "+963 999 250 603", "ميرا سليمان", -125000, "SYP"],
        ["علاء الدين", "+963 999 250 601", "ليان علاء الدين", 750000, "SYP"],
        ["هيفاء نعمة", "+963 999 250 601", "جود نعمة", 680000, "SYP"],
        ["بشار الأيوبي", "", "رهف الأيوبي", 920000, "SYP"],
        ["لمياء شديد", "12345", "جاد شديد", 510000, "SYP"],
        ["كميل حرب", "٠٠٠٠", "لارا حرب", 1110000, "SYP"],
        ["نور الدين", "+963 999 250 609", "سحر الدين", 0, "SYP"],
        ["سحر عباس", "+963 999 250 610", "زياد عباس", 1340000, "SYP"],
    ]
    for offset, values in enumerate(rows):
        _data_row(ws, 5 + offset, values, rtl=True, shade=offset % 2 == 1)
    _widths(ws, [24, 20, 24, 18, 10])
    return _save(wb, "xlsx-15-invalid-zero-negative-duplicates.xlsx")


# ---------------------------------------------------------------------------
# Metadata used by generate_all.py
# ---------------------------------------------------------------------------

FIXTURES: list[dict[str, Any]] = [
    {
        "file": "xlsx-01-standard-ar-multisheet.xlsx",
        "builder": build_x01_standard_ar_multisheet,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "SYP",
        "expected_warnings": ["SHEET_AUTO_SELECTED"],
        "supports_full_confirm": True,
        "notes": "Arabic RTL, two title rows, three sheets (statement/contacts/notes); statement sheet must be auto-selected.",
    },
    {
        "file": "xlsx-02-standard-en-headers.xlsx",
        "builder": build_x02_standard_en_headers,
        "kind": "xlsx",
        "expected_min_rows": 7,
        "expected_currency": "USD",
        "expected_warnings": [],
        "supports_full_confirm": True,
        "notes": "English LTR headers and values, USD amounts, single clean sheet.",
    },
    {
        "file": "xlsx-03-mixed-headers-extra-columns.xlsx",
        "builder": build_x03_mixed_extra_columns,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "SYP",
        "expected_warnings": ["ZERO_BALANCE", "SHARED_PHONE"],
        "supports_full_confirm": False,
        "notes": "Mixed Arabic/English headers plus irrelevant columns; includes one zero balance and one phone shared by different guardians.",
    },
    {
        "file": "xlsx-04-header-at-row-7.xlsx",
        "builder": build_x04_header_row_seven,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "SYP",
        "expected_warnings": [],
        "supports_full_confirm": True,
        "notes": "Header row is row 7; title, subtitle and notes occupy rows 1-6.",
    },
    {
        "file": "xlsx-05-headerless-3col-school-currency.xlsx",
        "builder": build_x05_headerless_three_columns,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "SYP",
        "expected_warnings": ["HEADER_NOT_FOUND", "CURRENCY_FROM_SCHOOL_SETTINGS"],
        "supports_full_confirm": False,
        "notes": "No header row; three columns (name, phone, amount). Currency is absent from the file and must come from school settings.",
    },
    {
        "file": "xlsx-06-headerless-5col.xlsx",
        "builder": build_x06_headerless_five_columns,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "SYP",
        "expected_warnings": ["HEADER_NOT_FOUND"],
        "supports_full_confirm": False,
        "notes": "No header row; five columns (name, phone, remaining, currency, student), including one zero balance for validation.",
    },
    {
        "file": "xlsx-07-merged-headers-guardians.xlsx",
        "builder": build_x07_merged_headers_guardians,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "SYP",
        "expected_warnings": [],
        "supports_full_confirm": True,
        "notes": "Merged header group cells and merged guardian name/phone cells for sibling rows.",
    },
    {
        "file": "xlsx-08-arabic-indic-digits-lira.xlsx",
        "builder": build_x08_arabic_indic_digits,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "SYP",
        "expected_warnings": [],
        "supports_full_confirm": True,
        "notes": "Arabic-Indic digits, Arabic decimal separator U+066B, Arabic thousands separator U+066C, and ل.س suffixes.",
    },
    {
        "file": "xlsx-09-multi-currency-syp-usd.xlsx",
        "builder": build_x09_multi_currency,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": None,
        "expected_warnings": [],
        "supports_full_confirm": True,
        "notes": "Mixed SYP and USD rows with a real currency column; totals must be grouped by currency.",
    },
    {
        "file": "xlsx-10-no-currency-col-usd-title.xlsx",
        "builder": build_x10_no_currency_column_usd_title,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "USD",
        "expected_warnings": [],
        "supports_full_confirm": True,
        "notes": "No currency column; title states USD and دولار, so document-level currency detection must yield USD.",
    },
    {
        "file": "xlsx-11-shuffled-column-order.xlsx",
        "builder": build_x11_shuffled_columns,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "SYP",
        "expected_warnings": [],
        "supports_full_confirm": True,
        "notes": "Phone first, money columns scattered, names last; header-based mapping must ignore column order.",
    },
    {
        "file": "xlsx-12-cover-before-statement.xlsx",
        "builder": build_x12_cover_before_statement,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "SYP",
        "expected_warnings": ["SHEET_AUTO_SELECTED"],
        "supports_full_confirm": True,
        "notes": "Cover and notes sheets precede the statement sheet; statement must be selected automatically.",
    },
    {
        "file": "xlsx-13-wide-empty-cols-footer.xlsx",
        "builder": build_x13_wide_empty_footer,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "SYP",
        "expected_warnings": ["MISSING_PHONE"],
        "supports_full_confirm": False,
        "notes": "Wide sheet with empty interleaved columns and blank rows before a totals/footer row; footer may be parsed as a non-confirmable row.",
    },
    {
        "file": "xlsx-14-formulas-cached-values.xlsx",
        "builder": build_x14_formulas_cached,
        "kind": "xlsx",
        "expected_min_rows": 6,
        "expected_currency": "SYP",
        "expected_warnings": ["FORMULA_WITHOUT_CACHED_VALUE", "MISSING_BALANCE"],
        "supports_full_confirm": False,
        "notes": "Five remaining-balance formulas have cached values; the last formula intentionally has no cached value and must be flagged.",
    },
    {
        "file": "xlsx-15-invalid-zero-negative-duplicates.xlsx",
        "builder": build_x15_invalid_values,
        "kind": "xlsx",
        "expected_min_rows": 10,
        "expected_currency": "SYP",
        "expected_warnings": [
            "ZERO_BALANCE",
            "NEGATIVE_BALANCE",
            "DUPLICATE_ROW",
            "SHARED_PHONE",
            "MISSING_PHONE",
            "INVALID_PHONE",
        ],
        "supports_full_confirm": False,
        "notes": "Validation matrix: zero, negative, duplicate row, shared phone with a different guardian, missing phone, and invalid phones.",
    },
]


def generate_all() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for fixture in FIXTURES:
        path = fixture["builder"]()
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f"XLSX fixture was not written: {path}")
        generated.append(path)
        print(f"[xlsx] {path.name} ({path.stat().st_size} bytes)")
    return generated


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        generate_all()
    except Exception as exc:  # pragma: no cover - CLI diagnostics
        print(f"XLSX fixture generation failed: {exc}", file=sys.stderr)
        raise
