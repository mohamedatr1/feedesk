/**
 * Generate synthetic PDF import-acceptance fixtures for FeeDesk.
 *
 * Text PDFs are rendered from HTML with Playwright Chromium.  The two scanned
 * fixtures are first rendered to PNG, then embedded as the only page content
 * so the resulting PDF has no extractable text layer.
 *
 * All names, phones and amounts below are fabricated.  No network access is
 * used beyond the local Chromium binary shipped with apps/web/node_modules.
 *
 * Usage:
 *   node scripts/qa_fixtures/generate_pdf.mjs
 */

import { chromium } from "../../apps/web/node_modules/playwright/index.mjs";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../..");
const OUT_DIR = path.join(ROOT, ".local", "samples", "qa");

const AR_FONT = "Tahoma, 'Segoe UI', Arial, sans-serif";
const EN_FONT = "Calibri, 'Segoe UI', Arial, sans-serif";

const BASE_CSS = `
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { color: #1b2430; background: #ffffff; }
  .sheet { padding: 22px 24px 30px; }
  h1 { margin: 0 0 4px; font-size: 19px; color: #1f3864; }
  .sub { margin: 0 0 14px; font-size: 10.5px; color: #58657a; }
  table { border-collapse: collapse; width: 100%; font-size: 10.5px; }
  th, td { padding: 6px 7px; vertical-align: top; }
  .bordered th, .bordered td { border: 1px solid #9fb1c7; }
  .bordered th { background: #0f6b78; color: #ffffff; font-weight: 700; }
  .zebra tbody tr:nth-child(even) td { background: #f1f5fa; }
  .num { text-align: left; font-variant-numeric: tabular-nums; white-space: nowrap; }
  [dir="rtl"] .num { text-align: right; }
  tfoot td { background: #e8eff7; font-weight: 700; border-top: 2px solid #1f3864; }
  .muted { color: #58657a; }
  .small { font-size: 9px; }
  .title-ar { direction: rtl; text-align: center; font-family: ${AR_FONT}; }
  .title-en { direction: ltr; text-align: left; font-family: ${EN_FONT}; }
  .footer-note { margin-top: 12px; font-size: 9.5px; color: #58657a; }
  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    thead { display: table-header-group; }
    tfoot { display: table-footer-group; }
    tr { page-break-inside: avoid; }
  }
`;

function esc(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function arabicPage({ title, subtitle, table, footer = "", extraStyle = "" }) {
  return `<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>${BASE_CSS}${extraStyle}
  body { font-family: ${AR_FONT}; }
  .sheet { direction: rtl; }
</style>
</head>
<body>
<div class="sheet">
  <h1>${esc(title)}</h1>
  <p class="sub">${esc(subtitle)}</p>
  ${table}
  ${footer ? `<p class="footer-note">${esc(footer)}</p>` : ""}
</div>
</body>
</html>`;
}

function englishPage({ title, subtitle, table, footer = "", extraStyle = "" }) {
  return `<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<style>${BASE_CSS}${extraStyle}
  body { font-family: ${EN_FONT}; }
</style>
</head>
<body>
<div class="sheet">
  <h1>${esc(title)}</h1>
  <p class="sub">${esc(subtitle)}</p>
  ${table}
  ${footer ? `<p class="footer-note">${esc(footer)}</p>` : ""}
</div>
</body>
</html>`;
}

function tableHtml(headers, rows, { bordered = true, zebra = true, foot = null, classes = "" } = {}) {
  const head = headers
    ? `<thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>`
    : "";
  const body = `<tbody>${rows
    .map((row) => `<tr>${row.map((cell) => `<td>${cell === null ? "" : esc(cell)}</td>`).join("")}</tr>`)
    .join("")}</tbody>`;
  const footer = foot
    ? `<tfoot><tr>${foot.map((cell) => `<td>${cell === null ? "" : esc(cell)}</td>`).join("")}</tr></tfoot>`
    : "";
  return `<table class="${bordered ? "bordered" : ""} ${zebra ? "zebra" : ""} ${classes}">${head}${body}${footer}</table>`;
}

// Deterministic, synthetic name pools.  Combining indices keeps every row
// unique without ever touching real personal data.
const AR_FIRST = [
  "ريم", "عمر", "سلمى", "خالد", "نورا", "بشار", "ليان", "آدم", "جودي", "ماريا",
  "زين", "لين", "هيثم", "غادة", "أنس", "ريما", "وليد", "ميرا", "سمير", "هالة",
  "مازن", "روان", "نبيل", "جنى", "فؤاد", "عبير", "سامي", "لينا", "مخلص", "هند",
  "غسان", "إيمان", "رامي", "سارة", "كرم", "دانية", "جورج", "أمل", "باسل", "ديما",
  "عماد", "ليلى", "رند", "شادي", "غالية", "مروان", "نادين", "فارس", "إياد", "سوسن",
];
const AR_LAST = [
  "القاسم", "الحمصي", "النعيمي", "الشامي", "العلي", "الحلبي", "درويش", "مرعي",
  "شعبان", "خوري", "سلوم", "جبور", "عيد", "صباغ", "قطان", "حجو", "زين", "عوض",
  "جمال", "حمدان", "عيسى", "بركات", "دياب", "علوش", "خليل", "سليمان", "عبود",
  "ملحم", "حنا", "ناصر", "حداد", "الشيخ", "عدرا", "زريق", "الحسن", "فرحات",
];
const EN_FIRST = [
  "Maya", "Omar", "Lina", "Ziad", "Rana", "Tarek", "Dima", "Leen", "Yara", "Karim",
  "Dana", "Sami", "Nour", "Elie", "Rita", "Jad", "Mira", "Hadi", "Sara", "Fadi",
];
const EN_LAST = [
  "Haddad", "Nassar", "Farah", "Mansour", "Kassem", "Aziz", "Rizk", "Khoury",
  "Salem", "Ayoub", "Hamwi", "Sayegh", "Barakat", "Nemeh", "Shaar", "Rihawi",
];

function arName(index) {
  return `${AR_FIRST[index % AR_FIRST.length]} ${AR_LAST[Math.floor(index / AR_FIRST.length) % AR_LAST.length]}`;
}

function enName(index) {
  return `${EN_FIRST[index % EN_FIRST.length]} ${EN_LAST[Math.floor(index / EN_FIRST.length) % EN_LAST.length]}`;
}

function arPhone(index, prefix = "944") {
  const block = String(300 + (Math.floor(index / 100) % 700)).padStart(3, "0");
  const tail = String(100 + (index % 100)).padStart(3, "0");
  return `+963 ${prefix} ${block} ${tail}`;
}

function enPhone(index, prefix = "933") {
  return arPhone(index, prefix);
}

// ---------------------------------------------------------------------------
// Fixture definitions
// ---------------------------------------------------------------------------

async function buildArabicBordered() {
  const rows = Array.from({ length: 7 }, (_, i) => [
    arName(i + 100),
    arName(i + 130),
    arPhone(i + 100, "944"),
    `الصف ${["الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس", "السابع"][i]}`,
    (750000 + i * 115000).toLocaleString("en-US"),
    "SYP",
  ]);
  const total = rows.reduce((sum, row) => sum + Number(row[4].replaceAll(",", "")), 0);
  return arabicPage({
    title: "PDF-P01 — مدرسة الياسمين — كشف أقساط عربي بإطار",
    subtitle: "جدول عربي من اليمين إلى اليسار مع حدود وخلايا مالية — بيانات اصطناعية",
    table: tableHtml(
      ["اسم الطالب", "اسم ولي الأمر", "رقم الهاتف", "الصف", "المتبقي", "العملة"],
      rows,
      { foot: ["الإجمالي", "", "", "", total.toLocaleString("en-US"), "SYP"] },
    ),
    footer: "العملة: الليرة السورية (ل.س) — ملف اختبار قبول الاستيراد.",
  });
}

async function buildEnglishBordered() {
  const rows = Array.from({ length: 7 }, (_, i) => [
    enName(i + 10),
    enName(i + 40),
    enPhone(i + 10, "933"),
    ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"][i],
    (320 + i * 55.5).toFixed(2),
    "USD",
  ]);
  const total = rows.reduce((sum, row) => sum + Number(row[4]), 0);
  return englishPage({
    title: "PDF-P02 — Al-Noor International School — Statement",
    subtitle: "English LTR bordered table with USD balances — synthetic acceptance fixture",
    table: tableHtml(
      ["Student Name", "Guardian Name", "Phone Number", "Grade", "Remaining Balance", "Currency"],
      rows,
      { foot: ["Total", "", "", "", total.toFixed(2), "USD"] },
    ),
    footer: "Currency: USD. Generated locally; no real personal data.",
  });
}

async function buildMultiPageRepeatedHeaders() {
  const rows = Array.from({ length: 48 }, (_, i) => [
    arName(i),
    arName(i + 60),
    arPhone(i, i % 2 === 0 ? "944" : "988"),
    `شعبة ${String.fromCharCode(0x0623 + (i % 4))}`,
    (450000 + i * 37000).toLocaleString("en-US"),
    "SYP",
  ]);
  return arabicPage({
    title: "PDF-P03 — كشف متعدد الصفحات مع تكرار الترويسة",
    subtitle: "48 صفًا اصطناعيًا؛ يجب أن تتكرر الترويسة أعلى كل صفحة عند الطباعة",
    table: tableHtml(
      ["اسم الطالب", "اسم ولي الأمر", "رقم الهاتف", "الشعبة", "المتبقي", "العملة"],
      rows,
    ),
    footer: "أرقام وأسماء ومبالغ تجريبية. العملة: SYP.",
    extraStyle: "table { font-size: 9.2px; } td, th { padding: 4px 6px; }",
  });
}

async function buildBorderlessTextColumns() {
  const rows = Array.from({ length: 6 }, (_, i) => [
    enName(i + 70),
    enPhone(i + 70, "999"),
    (540 + i * 63.25).toFixed(2),
    "SYP",
  ]);
  return englishPage({
    title: "PDF-P04 — Borderless text-column statement",
    subtitle: "No cell borders; columns separated by alignment and whitespace only",
    table: tableHtml(
      ["Guardian", "Telephone", "Balance", "Currency"],
      rows,
      { bordered: false, zebra: false, classes: "borderless" },
    ),
    footer: "Currency: SYP. Synthetic fixture for whitespace-based table extraction.",
    extraStyle: `
      .borderless th { background: #ffffff; color: #1f3864; border-bottom: 2px solid #1f3864; text-align: left; }
      .borderless td { border: 0; padding: 7px 8px; }
      .borderless td:nth-child(1) { width: 34%; }
      .borderless td:nth-child(2) { width: 30%; }
      .borderless td:nth-child(3) { width: 22%; }
    `,
  });
}

async function buildHeaderlessTable() {
  const rows = Array.from({ length: 6 }, (_, i) => [
    arName(i + 140),
    arPhone(i + 140, "944"),
    (620000 + i * 91000).toLocaleString("en-US") + " ل.س",
  ]);
  return arabicPage({
    title: "PDF-P05 — كشف بلا ترويسة (اسم، هاتف، مبلغ)",
    subtitle: "لا يوجد صف ترويسة؛ ثلاثة أعمدة فقط والعملة مذكورة في العنوان",
    table: tableHtml(null, rows, { bordered: false, zebra: false }),
    footer: "العملة: ل.س — يجب أن يستنتج المستورد الأعمدة من القيم.",
    extraStyle: `
      table { margin-top: 10px; }
      td { border-bottom: 1px dotted #c5d1df; padding: 8px 6px; }
      td:nth-child(1) { width: 42%; }
      td:nth-child(2) { width: 32%; }
      td:nth-child(3) { width: 26%; text-align: left; }
    `,
  });
}

async function buildMultilineWrappedCells() {
  const longClasses = [
    "الصف الخامس — شعبة العلوم التجريبية / الفوج ب",
    "الصف الرابع — شعبة الآداب واللغات / الفوج أ",
    "الصف السادس — شعبة المعلوماتية / الفوج ج",
    "الصف الثالث — شعبة التعليم العام / الفوج د",
    "الصف الثاني — شعبة اللغات الأجنبية / الفوج هـ",
  ];
  const rows = longClasses.map((className, i) => [
    arName(i + 170),
    arName(i + 190),
    arPhone(i + 170, i % 2 === 0 ? "988" : "999"),
    className,
    (710000 + i * 88000).toLocaleString("en-US"),
    "SYP",
  ]);
  return arabicPage({
    title: "PDF-P06 — خلايا متعددة الأسطر وأسماء صفوف ملتفة",
    subtitle: "أعمدة ضيقة تُجبر أسماء الصفوف الطويلة على الالتفاف داخل الخلية",
    table: tableHtml(
      ["اسم الطالب", "اسم ولي الأمر", "رقم الهاتف", "الصف والشعبة", "المتبقي", "العملة"],
      rows,
    ),
    footer: "العملة: SYP. اختبر استخراج الخلايا الملتفة دون دمج أسطر خاطئ.",
    extraStyle: `
      td, th { font-size: 9.5px; }
      td:nth-child(4), th:nth-child(4) { width: 31%; line-height: 1.5; }
      td:nth-child(1), th:nth-child(1) { width: 15%; }
      td:nth-child(2), th:nth-child(2) { width: 15%; }
      td:nth-child(3), th:nth-child(3) { width: 14%; }
    `,
  });
}

async function buildLandscapeRotated() {
  const rows = Array.from({ length: 8 }, (_, i) => [
    enName(i + 90),
    enName(i + 110),
    enPhone(i + 90, "944"),
    (1150 + i * 125).toFixed(2),
    "USD",
    `2026-${String(9 + (i % 3)).padStart(2, "0")}-15`,
  ]);
  return englishPage({
    title: "PDF-P07 — Landscape statement with rotated column headers",
    subtitle: "A4 landscape orientation; header labels are rotated vertically",
    table: tableHtml(
      ["Student", "Guardian", "Phone", "Remaining", "Currency", "Due Date"],
      rows,
      { foot: ["Total", "", "", rows.reduce((s, r) => s + Number(r[3]), 0).toFixed(2), "USD", ""] },
    ),
    footer: "Currency: USD. Landscape fixture for page-orientation detection.",
    extraStyle: `
      @page { size: A4 landscape; margin: 10mm; }
      .sheet { padding: 10px 14px 16px; width: 100%; }
      th { height: 74px; vertical-align: bottom; padding: 4px; }
      th span { display: inline-block; writing-mode: vertical-rl; transform: rotate(180deg); white-space: nowrap; }
    `,
  });
}

async function buildMixedTitleFooterCurrency() {
  const rows = Array.from({ length: 6 }, (_, i) => [
    arName(i + 210),
    arPhone(i + 210, i % 2 === 0 ? "933" : "944"),
    enName(i + 130),
    (240 + i * 47.5).toFixed(2),
    "Grade " + (i + 2),
  ]);
  return arabicPage({
    title: "PDF-P10 — Mixed Arabic/English statement — كشف مختلط",
    subtitle: "جدول مختلط بلا عمود عملة؛ العملة مذكورة في العنوان والتذييل فقط (USD / دولار)",
    table: tableHtml(
      ["اسم ولي الأمر", "رقم الهاتف", "Student Name", "المتبقي", "Grade"],
      rows,
      { foot: ["الإجمالي / Total", "", "", rows.reduce((s, r) => s + Number(r[3]), 0).toFixed(2), ""] },
    ),
    footer: "العملة: دولار أمريكي (USD). Currency in title/footer only.",
    extraStyle: "td, th { font-size: 10px; }",
  });
}

async function buildTotalsZeroInvalid() {
  const rows = [
    ["سامر الحلبي", "+963 999 260 701", "ليان الحلبي", "0", "SYP"],
    ["نورا عبد الرحمن", "+963 999 260 702", "جودي عبد الرحمن", "-75000", "SYP"],
    ["فادي مارون", "12345", "ماريا مارون", "640000", "SYP"],
    ["منى الشامي", "", "خالد الشامي", "920000", "SYP"],
    ["جورج حداد", "+963 999 260 705", "ريك حداد", "125000", "SYP"],
    ["أمل الشيخ", "+963 999 260 706", "ليان الشيخ", "0", "SYP"],
    ["باسل عدرا", "+963 999 260 707", "مروان عدرا", "480000", "SYP"],
  ];
  return arabicPage({
    title: "PDF-P11 — صف إجمالي وقيم صفرية وسالبة وهواتف غير صالحة",
    subtitle: "اختبار تحقق: ZERO_BALANCE وNEGATIVE_BALANCE وMISSING_PHONE وINVALID_PHONE",
    table: tableHtml(
      ["اسم ولي الأمر", "رقم الهاتف", "اسم الطالب", "المتبقي", "العملة"],
      rows,
      { foot: ["الإجمالي", "", "", "2,090,000", "SYP"] },
    ),
    footer: "العملة: SYP. الصف الأخير إجمالي وليس صف بيانات حقيقيًا.",
  });
}

// Scanned fixtures are built from the same HTML, screenshotted at 2x, then
// embedded as the sole content of the PDF.
async function buildScannedArabic(page, target) {
  const rows = Array.from({ length: 8 }, (_, i) => [
    arName(i + 230),
    arName(i + 250),
    arPhone(i + 230, i % 2 === 0 ? "988" : "999"),
    (830000 + i * 96000).toLocaleString("en-US"),
    "SYP",
  ]);
  const html = arabicPage({
    title: "PDF-P08 — نسخة ممسوحة ضوئيًا — كشف أقساط عربي",
    subtitle: "هذه الصفحة صورة فقط بلا طبقة نصية — اختبار OCR",
    table: tableHtml(
      ["اسم الطالب", "اسم ولي الأمر", "رقم الهاتف", "المتبقي", "العملة"],
      rows,
      { foot: ["الإجمالي", "", "", "9,940,000", "SYP"] },
    ),
    footer: "العملة: SYP. صورة مولدة محليًا لأغراض الاختبار.",
    extraStyle: "body { background: #fdfdfb; }",
  });
  await renderScanned(page, html, target);
}

async function buildScannedEnglish(page, target) {
  const rows = Array.from({ length: 7 }, (_, i) => [
    enName(i + 150),
    enName(i + 170),
    enPhone(i + 150, i % 2 === 0 ? "933" : "944"),
    (390 + i * 72.25).toFixed(2),
    "USD",
  ]);
  const html = englishPage({
    title: "PDF-P09 — Scanned copy — English fee statement",
    subtitle: "Image-only page with no text layer; OCR acceptance fixture",
    table: tableHtml(
      ["Student Name", "Guardian Name", "Phone Number", "Remaining Balance", "Currency"],
      rows,
      { foot: ["Total", "", "", rows.reduce((s, r) => s + Number(r[3]), 0).toFixed(2), "USD"] },
    ),
    footer: "Currency: USD. Locally generated image fixture.",
    extraStyle: "body { background: #fdfdfb; }",
  });
  await renderScanned(page, html, target);
}

async function renderScanned(page, html, target) {
  await page.setViewportSize({ width: 1000, height: 1400 });
  await page.setContent(html, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  await page.emulateMedia({ media: "print" });
  const png = await page.screenshot({ fullPage: true, type: "png" });
  const base64 = Buffer.from(png).toString("base64");
  const imageHtml = `<!doctype html>
<html><head><meta charset="utf-8">
<style>
  @page { size: A4; margin: 0; }
  html, body { margin: 0; padding: 0; background: #fff; }
  img { display: block; width: 100%; height: auto; }
</style></head>
<body><img src="data:image/png;base64,${base64}"></body></html>`;
  await page.setContent(imageHtml, { waitUntil: "load" });
  await page.pdf({ path: target, format: "A4", printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });
}

const FIXTURES = [
  {
    file: "pdf-01-arabic-rtl-bordered.pdf",
    build: buildArabicBordered,
    expected_min_rows: 7,
    expected_currency: "SYP",
    expected_warnings: [],
    supports_full_confirm: true,
    expected_text: true,
    notes: "Arabic RTL bordered table with title, header, 7 rows and a totals row; text layer required.",
  },
  {
    file: "pdf-02-english-ltr-table.pdf",
    build: buildEnglishBordered,
    expected_min_rows: 7,
    expected_currency: "USD",
    expected_warnings: [],
    supports_full_confirm: true,
    expected_text: true,
    notes: "English LTR bordered table with USD amounts and a totals row.",
  },
  {
    file: "pdf-03-multipage-repeated-headers.pdf",
    build: buildMultiPageRepeatedHeaders,
    expected_min_rows: 48,
    expected_currency: "SYP",
    expected_warnings: [],
    supports_full_confirm: true,
    expected_text: true,
    notes: "Multi-page Arabic table; thead repeats on every page. Verify no rows are lost or duplicated.",
  },
  {
    file: "pdf-04-borderless-text-columns.pdf",
    build: buildBorderlessTextColumns,
    expected_min_rows: 6,
    expected_currency: "SYP",
    expected_warnings: [],
    supports_full_confirm: true,
    expected_text: true,
    notes: "Borderless table using alignment/whitespace; exercises text-position table extraction.",
  },
  {
    file: "pdf-05-headerless-data-table.pdf",
    build: buildHeaderlessTable,
    expected_min_rows: 6,
    expected_currency: "SYP",
    expected_warnings: ["HEADER_NOT_FOUND"],
    supports_full_confirm: false,
    expected_text: true,
    notes: "No header row; three columns (name, phone, amount) with currency stated in the title.",
  },
  {
    file: "pdf-06-multiline-wrapped-cells.pdf",
    build: buildMultilineWrappedCells,
    expected_min_rows: 5,
    expected_currency: "SYP",
    expected_warnings: [],
    supports_full_confirm: true,
    expected_text: true,
    notes: "Long class names wrap to multiple lines inside narrow cells; verify cell text is not split into extra rows.",
  },
  {
    file: "pdf-07-landscape-rotated-headers.pdf",
    build: buildLandscapeRotated,
    expected_min_rows: 8,
    expected_currency: "USD",
    expected_warnings: [],
    supports_full_confirm: true,
    expected_text: true,
    notes: "A4 landscape table with vertically rotated header labels and a totals row.",
  },
  {
    file: "pdf-08-scanned-arabic-table.pdf",
    build: buildScannedArabic,
    expected_min_rows: 8,
    expected_currency: "SYP",
    expected_warnings: ["SCANNED_PDF", "OCR_USED"],
    supports_full_confirm: false,
    expected_text: false,
    scanned: true,
    notes: "Image-only scanned Arabic table (PNG embedded in PDF); must trigger OCR and require manual review.",
  },
  {
    file: "pdf-09-scanned-english-table.pdf",
    build: buildScannedEnglish,
    expected_min_rows: 7,
    expected_currency: "USD",
    expected_warnings: ["SCANNED_PDF", "OCR_USED"],
    supports_full_confirm: false,
    expected_text: false,
    scanned: true,
    notes: "Image-only scanned English table (PNG embedded in PDF); must trigger OCR and require manual review.",
  },
  {
    file: "pdf-10-mixed-ar-en-title-footer-currency.pdf",
    build: buildMixedTitleFooterCurrency,
    expected_min_rows: 6,
    expected_currency: "USD",
    expected_warnings: [],
    supports_full_confirm: true,
    expected_text: true,
    notes: "Mixed Arabic/English table with no currency column; USD/دولار appears only in title/footer.",
  },
  {
    file: "pdf-11-totals-zero-invalid-values.pdf",
    build: buildTotalsZeroInvalid,
    expected_min_rows: 7,
    expected_currency: "SYP",
    expected_warnings: ["ZERO_BALANCE", "NEGATIVE_BALANCE", "MISSING_PHONE", "INVALID_PHONE"],
    supports_full_confirm: false,
    expected_text: true,
    notes: "Totals/footer plus intentional zero, negative, missing-phone and invalid-phone rows for validation tests.",
  },
];

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 900, height: 1200 }, deviceScaleFactor: 2 });
  const generated = [];

  try {
    for (const fixture of FIXTURES) {
      const target = path.join(OUT_DIR, fixture.file);
      const isScanned = Boolean(fixture.scanned);

      if (isScanned) {
        await fixture.build(page, target);
      } else {
        await page.setViewportSize({ width: 900, height: 1200 });
        await page.setContent(await fixture.build(), { waitUntil: "load" });
        await page.evaluate(() => document.fonts.ready);
        await page.emulateMedia({ media: "print" });
        const landscape = fixture.file.includes("landscape");
        await page.pdf({
          path: target,
          format: "A4",
          landscape,
          printBackground: true,
          displayHeaderFooter: false,
          margin: landscape
            ? { top: "10mm", right: "10mm", bottom: "10mm", left: "10mm" }
            : { top: "14mm", right: "12mm", bottom: "14mm", left: "12mm" },
        });
      }

      const stat = await fs.stat(target);
      if (!stat.size) throw new Error(`Empty PDF: ${target}`);
      generated.push({ ...fixture, bytes: stat.size });
      console.log(`[pdf] ${fixture.file} (${stat.size} bytes)`);
    }
  } finally {
    await page.close();
    await browser.close();
  }

  const sidecar = generated.map(({ build, ...meta }) => meta);
  await fs.writeFile(
    path.join(OUT_DIR, ".pdf_manifest.partial.json"),
    JSON.stringify(sidecar, null, 2),
    "utf8",
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
