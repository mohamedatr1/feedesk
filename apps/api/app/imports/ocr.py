"""Assisted OCR for scanned PDF pages.

The engine is local Tesseract only.  OCR output is deliberately *assisted*:
callers stage the reconstructed rows and let the normal validation/review
pipeline decide what is usable.  Nothing here marks a row eligible.
"""

from __future__ import annotations

import csv
import io
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import ROOT, settings
from .normalization import auto_suggest_mapping

# Bidi controls and directional marks leak into Tesseract TSV output and make
# otherwise valid headers/phones impossible to match.
_BIDI_CONTROLS = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
_ARABIC_CHAR = re.compile(r"[\u0600-\u06ff\u0750-\u077f]")
_CELL_GAP_AT_300DPI = 28.0


@dataclass(frozen=True)
class OcrWord:
    block: int
    paragraph: int
    line: int
    word: int
    left: int
    top: int
    width: int
    height: int
    confidence: float
    text: str


@dataclass
class OcrPage:
    rows: list[list[str]]
    text: str
    mean_confidence: float


def clean_ocr_text(value: object) -> str:
    """Strip bidi controls and repair OCR phone tokens like ``963...101+``."""
    if value is None:
        return ""
    text = _BIDI_CONTROLS.sub("", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    if (
        text.endswith("+")
        and "+" not in text[:-1]
        and any(character.isdigit() for character in text[:-1])
    ):
        text = "+" + text[:-1].rstrip()
    return text


def tesseract_path() -> str | None:
    command = (settings.ocr_tesseract_cmd or "").strip()
    if command:
        found = shutil.which(command)
        if found:
            return found
        candidate = Path(command)
        if candidate.is_file():
            return str(candidate)
        return None
    return shutil.which("tesseract")


def tessdata_dir() -> Path | None:
    configured = (settings.ocr_tessdata_dir or "").strip()
    candidate = Path(configured) if configured else ROOT / ".local" / "tessdata"
    if not candidate.is_dir():
        return None
    for language in settings.ocr_languages.split("+"):
        language = language.strip()
        if language and not (candidate / f"{language}.traineddata").is_file():
            return None
    return candidate


def is_available() -> bool:
    return tesseract_path() is not None and tessdata_dir() is not None


def parse_tsv(text: str) -> list[OcrWord]:
    """Parse Tesseract TSV output into level-5 word records."""
    text = text.lstrip("\ufeff")
    if not text.strip():
        return []
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    words: list[OcrWord] = []
    for row in reader:
        if (row.get("level") or "").strip() != "5":
            continue
        word_text = clean_ocr_text(row.get("text"))
        if not word_text:
            continue
        try:
            words.append(
                OcrWord(
                    block=int(row["block_num"]),
                    paragraph=int(row["par_num"]),
                    line=int(row["line_num"]),
                    word=int(row["word_num"]),
                    left=int(row["left"]),
                    top=int(row["top"]),
                    width=int(row["width"]),
                    height=int(row["height"]),
                    confidence=float(row["conf"]),
                    text=word_text,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return words


def _line_cells(
    line_words: list[OcrWord],
    *,
    gap_threshold: float,
    reverse_words: bool,
) -> list[str]:
    ordered = sorted(line_words, key=lambda item: (item.left, item.top))
    grouped: list[list[OcrWord]] = []
    current: list[OcrWord] = []
    previous_right: float | None = None
    for word in ordered:
        if (
            previous_right is not None
            and word.left - previous_right > gap_threshold
        ):
            grouped.append(current)
            current = []
        current.append(word)
        previous_right = max(previous_right or 0.0, word.left + word.width)
    if current:
        grouped.append(current)

    cells: list[str] = []
    for group in grouped:
        if reverse_words:
            group = list(reversed(group))
        cells.append(clean_ocr_text(" ".join(word.text for word in group)))
    return cells


def _build_rows(
    words: list[OcrWord],
    *,
    gap_threshold: float,
    rtl: bool,
) -> list[list[str]]:
    grouped: dict[tuple[int, int, int], list[OcrWord]] = {}
    for word in words:
        grouped.setdefault(
            (word.block, word.paragraph, word.line), []
        ).append(word)

    rows: list[list[str]] = []
    for key in sorted(grouped):
        cells = _line_cells(
            grouped[key],
            gap_threshold=gap_threshold,
            reverse_words=rtl,
        )
        if rtl:
            cells = list(reversed(cells))
        if any(cells):
            rows.append(cells)
    return rows


def _arabic_ratio(rows: list[list[str]]) -> float:
    joined = "".join("".join(row) for row in rows)
    letters = [character for character in joined if not character.isspace()]
    if not letters:
        return 0.0
    return sum(1 for character in letters if _ARABIC_CHAR.match(character)) / len(
        letters
    )


def _mapping_score(rows: list[list[str]]) -> int:
    return sum(len(auto_suggest_mapping(row)) for row in rows)


def reconstruct_rows(
    words: list[OcrWord],
    *,
    gap_threshold: float = _CELL_GAP_AT_300DPI,
) -> list[list[str]]:
    """Rebuild table rows from OCR words.

    Tesseract emits words in visual (left-to-right) order.  Arabic statements
    are laid out right-to-left, so reversing both the cells and the words
    inside each cell restores logical reading order.  Both orientations are
    scored with the existing header-mapping synonyms and the better one wins.
    """
    ltr_rows = _build_rows(words, gap_threshold=gap_threshold, rtl=False)
    rtl_rows = _build_rows(words, gap_threshold=gap_threshold, rtl=True)
    ltr_score = _mapping_score(ltr_rows)
    rtl_score = _mapping_score(rtl_rows)
    if rtl_score > ltr_score:
        return rtl_rows
    if ltr_score > rtl_score:
        return ltr_rows
    if _arabic_ratio(rtl_rows) >= 0.5:
        return rtl_rows
    return ltr_rows


def ocr_page(page: Any) -> OcrPage | None:
    """Render and OCR one pdfplumber page, or return ``None`` on any failure."""
    executable = tesseract_path()
    data_dir = tessdata_dir()
    if executable is None or data_dir is None:
        return None

    try:
        rendered = page.to_image(resolution=settings.ocr_render_dpi)
    except Exception:
        return None

    with tempfile.TemporaryDirectory(prefix="feedesk-ocr-") as directory:
        png_path = Path(directory) / "page.png"
        try:
            rendered.save(str(png_path))
        except Exception:
            try:
                rendered.original.save(png_path)
            except Exception:
                return None

        # PSM 3 (fully automatic layout analysis) keeps table rows separated
        # when grid lines are present; PSM 6 collapses them into one line on
        # several scanned statements.  Fall back to PSM 6 for engines/pages
        # where automatic segmentation yields nothing.
        words: list[OcrWord] = []
        for psm in ("4", "6", "3"):
            command = [
                executable,
                str(png_path),
                "stdout",
                "--tessdata-dir",
                str(data_dir),
                "-l",
                settings.ocr_languages,
                "--psm",
                psm,
                "tsv",
            ]
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    timeout=settings.ocr_timeout_seconds,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            if completed.returncode != 0:
                continue
            try:
                output = completed.stdout.decode("utf-8")
            except UnicodeDecodeError:
                output = completed.stdout.decode("utf-8", errors="replace")
            words = parse_tsv(output)
            if words:
                break

    if not words:
        return None

    rows = reconstruct_rows(words)
    text = "\n".join(" ".join(row) for row in rows)
    mean_confidence = sum(word.confidence for word in words) / len(words)
    return OcrPage(rows=rows, text=text, mean_confidence=mean_confidence)
