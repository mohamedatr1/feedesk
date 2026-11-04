"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  FileSearch,
  Info,
  LoaderCircle,
  RotateCcw,
  TriangleAlert,
  Upload,
} from "lucide-react";
import {
  ApiError,
  api,
  formatNumber,
  importErrorMessage,
  uploadImport,
  type ColumnMapping,
  type ImportDetail,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { Dialog } from "@/components/Dialog";
import { FileDropzone, validateImportFile } from "@/components/imports/FileDropzone";
import { MappingTable, duplicateMappingFields } from "@/components/imports/MappingTable";
import { IssueList } from "@/components/imports/IssueList";
import { ImportStatusPill } from "@/components/imports/ImportStatusPill";
import { ImportCounts } from "@/components/imports/ImportCounts";

type Stage = "select" | "uploaded" | "sheets" | "mapping" | "result";

const STEPS = [
  { key: "select", label: "الملف" },
  { key: "sheets", label: "الورقة" },
  { key: "mapping", label: "الأعمدة" },
  { key: "result", label: "الاستخراج" },
];

function headerOptions(detail: ImportDetail | null): string[] {
  const headers = new Set<string>();
  (detail?.available_headers ?? []).forEach((header) => {
    if (header) headers.add(header);
  });
  Object.values(detail?.column_mapping ?? {}).forEach((header) => {
    if (header) headers.add(header);
  });
  return Array.from(headers);
}

function UploadContent() {
  const router = useRouter();
  const { settings } = useSession();
  const [stage, setStage] = useState<Stage>("select");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState<number | null>(0);
  const [detail, setDetail] = useState<ImportDetail | null>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<ColumnMapping>({});
  const [suggested, setSuggested] = useState<ColumnMapping | null>(null);
  const [selectedSheet, setSelectedSheet] = useState("");
  const [duplicate, setDuplicate] = useState<{ existingImportId: string } | null>(null);
  const [duplicateReason, setDuplicateReason] = useState("");
  const [duplicateChecked, setDuplicateChecked] = useState(false);

  const busy = uploading || processing;
  const maxUploadMb = settings?.max_upload_mb ?? detail?.max_upload_mb ?? null;
  const currentStep =
    stage === "select" || stage === "uploaded"
      ? 0
      : stage === "sheets"
        ? 1
        : stage === "mapping"
          ? 2
          : 3;
  const failure = importErrorMessage(detail?.error_summary);
  const hasScannedWarning = Boolean(
    (detail?.warnings ?? []).some((warning) => warning.code === "SCANNED_PDF"),
  );
  const sheets = detail?.available_sheets ?? [];
  const totalRows = detail?.total_rows ?? 0;
  const currentSheet = detail?.worksheet_name ?? "";
  const multiSheet = sheets.length > 1;
  const reviewable =
    detail?.status === "review_required" || detail?.status === "ready_to_confirm";
  const canContinueToMapping =
    totalRows > 0 && (reviewable || detail?.status === "uploaded");
  const selectedIsCurrent = Boolean(selectedSheet) && selectedSheet === currentSheet;
  const duplicates = duplicateMappingFields(mapping);
  const missingRequired = [
    !mapping.guardian_name ? "اسم ولي الأمر" : null,
    !mapping.remaining_balance ? "المتبقي" : null,
    !mapping.currency ? "العملة" : null,
  ].filter(Boolean) as string[];

  useEffect(() => {
    const resumeId = new URLSearchParams(window.location.search).get("import");
    if (!resumeId) return;
    let mounted = true;
    (async () => {
      try {
        const next = await api.getImport(resumeId);
        if (!mounted) return;
        setDetail(next);
        setSuggested(next.column_mapping ?? {});
        setMapping({ ...(next.column_mapping ?? {}) });
        if (
          next.status === "review_required" ||
          next.status === "ready_to_confirm"
        ) {
          await openMapping(next);
        } else if (
          next.status === "uploaded" &&
          (next.total_rows ?? 0) === 0 &&
          (next.available_sheets ?? []).length > 1
        ) {
          setSelectedSheet(next.worksheet_name ?? "");
          setStage("sheets");
        } else {
          setStage("uploaded");
        }
      } catch (err) {
        if (mounted) {
          setError(
            err instanceof ApiError ? err.messageAr : "تعذر استئناف هذا الاستيراد.",
          );
        }
      }
    })();
    return () => {
      mounted = false;
    };
    // Resume only once from the URL.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (stage === "uploaded") {
      document.getElementById("uploaded-title")?.focus();
    }
    if (stage === "sheets") {
      document.getElementById("sheet-title")?.focus();
    }
    if (stage === "result") {
      document
        .querySelector<HTMLElement>("[data-result-heading]")
        ?.focus();
    }
  }, [stage]);

  function openMapping(next: ImportDetail) {
    setDetail(next);
    setSuggested(next.column_mapping ?? {});
    setMapping({ ...(next.column_mapping ?? {}) });
    setHeaders(headerOptions(next));
    setError(null);
    setStage("mapping");
  }

  async function startUpload(forceDuplicate = false) {
    if (!file) return;
    const validation = validateImportFile(file, maxUploadMb);
    if (validation) {
      setFileError(validation);
      return;
    }
    if (forceDuplicate && duplicateReason.trim().length === 0) {
      setError("اذكر سبب رفع الملف مرة أخرى.");
      return;
    }

    setUploading(true);
    setProgress(0);
    setFileError(null);
    setError(null);
    try {
      const next = await uploadImport(file, {
        forceDuplicate,
        duplicateReason: forceDuplicate ? duplicateReason.trim() : undefined,
        onProgress: setProgress,
      });
      setDuplicate(null);
      setDuplicateChecked(false);
      setDetail(next);
      setSuggested(next.column_mapping ?? {});
      setMapping({ ...(next.column_mapping ?? {}) });
      // Explicit handoff: never advance the wizard automatically after upload.
      setStage("uploaded");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && err.code === "DUPLICATE_FILE") {
        const existing = err.details?.existing_import_id;
        setDuplicate({ existingImportId: typeof existing === "string" ? existing : "" });
        setDuplicateChecked(false);
        setError(null);
      } else if (err instanceof ApiError && (err.status === 422 || err.status === 413)) {
        setFileError(err.messageAr);
      } else if (err instanceof ApiError && err.status === 403) {
        setError("لا تملك صلاحية رفع الكشوف. تواصل مع مدير النظام.");
      } else {
        setError(err instanceof ApiError ? err.messageAr : "تعذر رفع الملف. حاول مرة أخرى.");
      }
    } finally {
      setUploading(false);
    }
  }

  function openSheets() {
    setError(null);
    setSelectedSheet(detail?.worksheet_name ?? "");
    setStage("sheets");
  }

  async function processSheet() {
    if (!detail || !selectedSheet) return;
    // The importer already staged this sheet; don't re-extract unless the user
    // actually picked a different one.
    if (selectedSheet === detail.worksheet_name && (detail.total_rows ?? 0) > 0) {
      openMapping(detail);
      return;
    }
    setProcessing(true);
    setError(null);
    try {
      const next = await api.processImport(detail.id, { worksheet_name: selectedSheet });
      await openMapping(next);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.messageAr
          : "تعذرت معالجة ورقة العمل المحددة. حاول مرة أخرى.",
      );
    } finally {
      setProcessing(false);
    }
  }

  async function extractRows() {
    if (!detail || duplicates.length > 0 || missingRequired.length > 0) return;
    const cleaned: ColumnMapping = Object.fromEntries(
      Object.entries(mapping).filter(([, value]) => Boolean(value)),
    );

    setProcessing(true);
    setError(null);
    try {
      const next = await api.processImport(detail.id, {
        worksheet_name: detail.worksheet_name ?? undefined,
        mapping: cleaned,
      });
      setDetail(next);
      // Explicit result panel. No auto-redirect to review.
      setStage("result");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.messageAr
          : "تعذر استخراج السجلات من الملف بهذا الربط. حاول مرة أخرى.",
      );
    } finally {
      setProcessing(false);
    }
  }

  function reset() {
    setFile(null);
    setDetail(null);
    setHeaders([]);
    setMapping({});
    setSuggested(null);
    setDuplicate(null);
    setDuplicateReason("");
    setDuplicateChecked(false);
    setError(null);
    setFileError(null);
    setProgress(0);
    setSelectedSheet("");
    setStage("select");
  }

  return (
    <>
      <PageHeader
        title="رفع كشف جديد"
        subtitle="ارفع ملف Excel أو PDF، وسنختار الورقة الأنسب تلقائيًا، ثم راجع مطابقة الأعمدة قبل الاستخراج."
        action={
          <Link href="/statements" className="fd-btn fd-btn-secondary h-11">
            <ArrowLeft size={16} aria-hidden />
            عودة للسجل
          </Link>
        }
      />

      <ol className="mb-5 flex flex-wrap items-center gap-2 text-[12px]" aria-label="خطوات رفع الكشف">
        {STEPS.map((step, index) => {
          const active = index === currentStep;
          const complete = index < currentStep;
          return (
            <li key={step.key} className="flex items-center gap-2">
              <span
                className={`flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-semibold ${
                  complete
                    ? "bg-[var(--fd-green-soft)] text-[var(--fd-green-text)]"
                    : active
                      ? "bg-[var(--fd-brand)] text-white"
                      : "bg-[var(--fd-surface-alt)] text-[var(--fd-ink-subtle)]"
                }`}
                aria-hidden
              >
                {complete ? "✓" : index + 1}
              </span>
              <span
                className={
                  active || complete
                    ? "font-medium text-[var(--fd-ink)]"
                    : "text-[var(--fd-ink-subtle)]"
                }
                aria-current={active ? "step" : undefined}
              >
                {step.label}
              </span>
              {index < STEPS.length - 1 && (
                <span className="mx-1 h-px w-5 bg-[var(--fd-line-strong)]" aria-hidden />
              )}
            </li>
          );
        })}
      </ol>

      {error && (
        <div
          role="alert"
          className="mb-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] text-[var(--fd-red-text)]"
        >
          {error}
        </div>
      )}

      {stage === "select" && (
        <div className="grid gap-5 lg:grid-cols-[1.4fr_0.6fr]">
          <section className="fd-card fd-card-pad" aria-labelledby="upload-file-title">
            <h2 id="upload-file-title" className="mb-4 text-sm font-semibold text-[var(--fd-ink)]">
              ملف الكشف
            </h2>

            <FileDropzone
              file={file}
              onFile={(next) => {
                setFile(next);
                setFileError(validateImportFile(next, maxUploadMb));
                setDuplicate(null);
                setError(null);
              }}
              onClear={reset}
              disabled={busy}
              error={fileError}
              maxUploadMb={maxUploadMb}
            />

            {uploading && (
              <div className="mt-4">
                <div className="mb-1.5 flex items-center justify-between text-[12px] text-[var(--fd-ink-muted)]">
                  <span>
                    {progress === null ? "جارٍ رفع الملف…" : `تم رفع ${progress}%`}
                  </span>
                </div>
                <div
                  className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--fd-surface-alt)]"
                  role="progressbar"
                  aria-valuemin={progress === null ? undefined : 0}
                  aria-valuemax={progress === null ? undefined : 100}
                  aria-valuenow={progress ?? undefined}
                  aria-label="تقدم رفع الملف"
                >
                  <div
                    className={`h-full rounded-full bg-[var(--fd-brand)] transition-[width] ${
                      progress === null ? "w-1/3 animate-pulse" : ""
                    }`}
                    style={progress === null ? undefined : { width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--fd-line)] pt-4">
              <p className="text-[11px] leading-5 text-[var(--fd-ink-subtle)]">
                لا يتم استخراج أي بيانات قبل تأكيد مطابقة الأعمدة.
              </p>
              <button
                type="button"
                className="fd-btn fd-btn-primary h-11"
                onClick={() => void startUpload(false)}
                disabled={!file || busy || Boolean(fileError)}
              >
                {uploading ? (
                  <LoaderCircle size={16} className="animate-spin" aria-hidden />
                ) : (
                  <Upload size={16} aria-hidden />
                )}
                {uploading ? "جارٍ الرفع…" : "رفع الملف"}
              </button>
            </div>
          </section>

          <aside className="fd-card fd-card-pad">
            <h2 className="text-sm font-semibold text-[var(--fd-ink)]">قبل الرفع</h2>
            <ul className="mt-3 space-y-2.5 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
              <li className="flex gap-2">
                <CheckCircle2 size={15} className="mt-1 shrink-0 text-[var(--fd-green)]" aria-hidden />
                استخدم كشفًا يحتوي على أعمدة واضحة لولي الأمر والهاتف والمتبقي.
              </li>
              <li className="flex gap-2">
                <CheckCircle2 size={15} className="mt-1 shrink-0 text-[var(--fd-green)]" aria-hidden />
                إذا كان الملف يحتوي عدة أوراق، سنختار الورقة الأنسب تلقائيًا ويمكنك تغييرها.
              </li>
              <li className="flex gap-2">
                <CheckCircle2 size={15} className="mt-1 shrink-0 text-[var(--fd-green)]" aria-hidden />
                يمكنك تعديل مطابقة الأعمدة قبل الاستخراج.
              </li>
              <li className="flex gap-2">
                <CheckCircle2 size={15} className="mt-1 shrink-0 text-[var(--fd-green)]" aria-hidden />
                الكشوف الممسوحة ضوئيًا تُقرأ بمساعدة OCR، وتتطلب مراجعة يدوية قبل التأكيد.
              </li>
            </ul>
          </aside>
        </div>
      )}

      {stage === "uploaded" && detail && (
        <section className="fd-card fd-card-pad max-w-3xl" aria-labelledby="uploaded-title">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2
                id="uploaded-title"
                tabIndex={-1}
                className="flex items-center gap-2 text-sm font-semibold text-[var(--fd-ink)]"
              >
                <CheckCircle2 size={17} className="text-[var(--fd-green)]" aria-hidden />
                تم رفع الملف
              </h2>
              <p className="mt-1 text-[12px] text-[var(--fd-ink-muted)]">
                <bdi dir="ltr">{detail.source_filename}</bdi>
                {detail.worksheet_name ? ` · ${detail.worksheet_name}` : ""}
              </p>
            </div>
            <ImportStatusPill status={detail.status} />
          </div>

          {detail.status === "failed" ? (
            <div className="mt-4">
              <p
                role="alert"
                className="rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] leading-6 text-[var(--fd-red-text)]"
              >
                <span className="font-semibold">تعذر تحليل الملف. </span>
                {failure ?? "تعذر تحليل الملف."}
              </p>
              <p className="mt-2 text-[12px] text-[var(--fd-ink-muted)]">
                لم تُنشأ أي سجلات مالية.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" className="fd-btn fd-btn-primary h-11" onClick={reset}>
                  رفع ملف آخر
                </button>
                <Link
                  href={`/statements/${detail.id}`}
                  className="fd-btn fd-btn-secondary h-11"
                >
                  عرض تفاصيل الاستيراد
                </Link>
              </div>
            </div>
          ) : (
            <>
              <div className="mt-4">
                <ImportCounts
                  total={totalRows}
                  valid={detail.valid_rows ?? 0}
                  invalid={detail.invalid_rows ?? 0}
                  duplicates={detail.duplicate_rows ?? 0}
                  excluded={detail.excluded_rows ?? undefined}
                />
              </div>

              {multiSheet && totalRows > 0 && currentSheet && (
                <p className="mt-4 flex items-start gap-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] px-3 py-2 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
                  <Info size={15} className="mt-1 shrink-0" aria-hidden />
                  <span>
                    اخترنا الورقة{" "}
                    <bdi className="font-medium text-[var(--fd-ink)]">{currentSheet}</bdi>{" "}
                    تلقائيًا واستخرجنا الأسطر منها. إذا كانت ورقة أخرى تحتوي على جدول
                    الأقساط، استخدم «تغيير الورقة» وسيُعاد الاستخراج.
                  </span>
                </p>
              )}

              {totalRows > 0 && missingRequired.length > 0 && (
                <p className="mt-3 flex items-start gap-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] px-3 py-2 text-[12px] leading-6 text-[var(--fd-amber-text)]">
                  <TriangleAlert size={15} className="mt-1 shrink-0" aria-hidden />
                  <span>
                    لم تُطابق بعض الحقول المطلوبة تلقائيًا ({missingRequired.join("، ")}).
                    يمكنك تحديدها يدويًا في خطوة مطابقة الأعمدة.
                  </span>
                </p>
              )}

              {totalRows === 0 && multiSheet && !hasScannedWarning && (
                <p className="mt-4 flex items-start gap-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] px-3 py-2 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
                  <Info size={15} className="mt-1 shrink-0" aria-hidden />
                  لم تُستخرج أي أسطر تلقائيًا. اختر الورقة التي تحتوي على جدول الأقساط
                  للمتابعة.
                </p>
              )}

              {hasScannedWarning && (
                <p className="mt-4 flex items-start gap-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] px-3 py-2 text-[12px] leading-6 text-[var(--fd-amber-text)]">
                  <Info size={15} className="mt-1 shrink-0" aria-hidden />
                  يبدو الملف ممسوحًا ضوئيًا وتعذر استخراج صفوف بمساعدة OCR. جرّب نسخة أوضح
                  أو أدخل البيانات يدويًا.
                </p>
              )}

              {(detail.warnings ?? []).length > 0 && (
                <IssueList issues={detail.warnings ?? []} className="mt-4" />
              )}

              <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--fd-line)] pt-4">
                <button
                  type="button"
                  className="fd-btn fd-btn-ghost h-11"
                  onClick={reset}
                  disabled={busy}
                >
                  <RotateCcw size={15} aria-hidden />
                  رفع ملف آخر
                </button>
                <div className="flex flex-wrap gap-2">
                  {canContinueToMapping ? (
                    <button
                      type="button"
                      className="fd-btn fd-btn-primary h-11"
                      onClick={() => void openMapping(detail)}
                      disabled={busy}
                    >
                      متابعة إلى مطابقة الأعمدة
                    </button>
                  ) : totalRows === 0 && multiSheet ? (
                    <button
                      type="button"
                      className="fd-btn fd-btn-primary h-11"
                      onClick={openSheets}
                      disabled={busy}
                    >
                      اختيار الورقة
                    </button>
                  ) : (
                    <Link
                      href={`/statements/${detail.id}`}
                      className="fd-btn fd-btn-primary h-11"
                    >
                      عرض تفاصيل الاستيراد
                    </Link>
                  )}
                  {totalRows > 0 && multiSheet && (
                    <button
                      type="button"
                      className="fd-btn fd-btn-secondary h-11"
                      onClick={openSheets}
                      disabled={busy}
                    >
                      تغيير الورقة
                    </button>
                  )}
                </div>
              </div>
            </>
          )}
        </section>
      )}

      {stage === "sheets" && detail && (
        <section className="fd-card fd-card-pad max-w-2xl" aria-labelledby="sheet-title">
          <h2
            id="sheet-title"
            tabIndex={-1}
            className="text-sm font-semibold text-[var(--fd-ink)]"
          >
            اختر الورقة التي تحتوي على جدول الأقساط
          </h2>
          <p
            id="sheet-help"
            className="mt-1 text-[12px] leading-6 text-[var(--fd-ink-muted)]"
          >
            عدد الورقات في الملف: {formatNumber(sheets.length)}.{" "}
            {currentSheet ? (
              <>
                الورقة المحددة حاليًا:{" "}
                <bdi className="font-medium text-[var(--fd-ink)]">{currentSheet}</bdi>
                {totalRows > 0 ? "، وقد استُخرجت الأسطر الحالية منها" : ""}. اختيار ورقة
                أخرى يعيد الاستخراج ويستبدل الأسطر الحالية.
              </>
            ) : (
              <>لم تُحدَّد ورقة بعد. اختر الورقة التي تحتوي على جدول الأقساط لبدء الاستخراج.</>
            )}
          </p>

          <div
            className="mt-4 space-y-2"
            role="radiogroup"
            aria-labelledby="sheet-title"
            aria-describedby="sheet-help"
          >
            {sheets.map((sheet) => {
              const isCurrent = sheet === currentSheet;
              const isSelected = selectedSheet === sheet;
              return (
                <label
                  key={sheet}
                  className={`flex min-h-[64px] cursor-pointer items-center gap-3 rounded-[var(--fd-radius-control)] border px-3 py-2 text-sm ${
                    isSelected
                      ? "border-2 border-[var(--fd-brand)] bg-[var(--fd-brand-soft)]"
                      : "border border-[var(--fd-line)] bg-[var(--fd-surface)]"
                  }`}
                >
                  <input
                    type="radio"
                    name="worksheet"
                    value={sheet}
                    checked={isSelected}
                    onChange={() => setSelectedSheet(sheet)}
                    disabled={busy}
                    className="h-4 w-4 shrink-0 accent-[var(--fd-brand)]"
                  />
                  <span className="flex flex-1 flex-wrap items-center gap-2">
                    <span className="font-medium text-[var(--fd-ink)]">
                      <bdi>{sheet}</bdi>
                    </span>
                    {isCurrent && (
                      <span className="fd-pill fd-pill-green">
                        <CheckCircle2 size={12} aria-hidden />
                        الورقة الحالية
                      </span>
                    )}
                  </span>
                  {isCurrent && totalRows > 0 && (
                    <span className="shrink-0 text-[11px] text-[var(--fd-ink-muted)]">
                      تم استخراج الأسطر
                    </span>
                  )}
                </label>
              );
            })}
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--fd-line)] pt-4">
            <button
              type="button"
              className="fd-btn fd-btn-secondary h-11"
              onClick={() => setStage("uploaded")}
              disabled={busy}
            >
              رجوع
            </button>
            <div className="text-end">
              {!selectedSheet && (
                <p id="sheet-required" className="mb-1 text-[11px] text-[var(--fd-red-text)]">
                  اختر ورقة للمتابعة.
                </p>
              )}
              {selectedSheet && !selectedIsCurrent && totalRows > 0 && (
                <p
                  id="sheet-reprocess-note"
                  className="mb-1 max-w-xs text-[11px] leading-5 text-[var(--fd-ink-subtle)]"
                >
                  سيُعاد استخراج الأسطر من الورقة الجديدة، وستُستبدل الأسطر الحالية.
                </p>
              )}
              <button
                type="button"
                className="fd-btn fd-btn-primary h-11"
                onClick={() => void processSheet()}
                disabled={busy || !selectedSheet}
                aria-describedby={
                  !selectedSheet
                    ? "sheet-required"
                    : selectedIsCurrent || totalRows === 0
                      ? "sheet-help"
                      : "sheet-help sheet-reprocess-note"
                }
              >
                {processing ? (
                  <LoaderCircle size={16} className="animate-spin" aria-hidden />
                ) : (
                  <FileSearch size={16} aria-hidden />
                )}
                {processing
                  ? "جارٍ تحليل الملف…"
                  : selectedIsCurrent && totalRows > 0
                    ? "متابعة إلى مطابقة الأعمدة"
                    : "استخراج هذه الورقة"}
              </button>
            </div>
          </div>
        </section>
      )}

      {stage === "mapping" && detail && (
        <div className="space-y-5">
          <section className="fd-card fd-card-pad" aria-labelledby="mapping-summary-title">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2
                  id="mapping-summary-title"
                  className="text-sm font-semibold text-[var(--fd-ink)]"
                >
                  <bdi dir="ltr">{detail.source_filename}</bdi>
                </h2>
                <p className="mt-1 text-[12px] text-[var(--fd-ink-muted)]">
                  {detail.worksheet_name ? `ورقة: ${detail.worksheet_name} · ` : ""}
                  الأسطر المقروءة: {formatNumber(detail.total_rows ?? 0)}
                </p>
              </div>
              <ImportStatusPill status={detail.status} />
            </div>

            {(detail.warnings ?? []).length > 0 && (
              <IssueList issues={detail.warnings ?? []} className="mt-3" />
            )}

            {failure && (
              <p
                role="alert"
                className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] leading-6 text-[var(--fd-red-text)]"
              >
                {failure}
              </p>
            )}
          </section>

          {(detail.total_rows ?? 0) === 0 ? (
            <section className="fd-card">
              <EmptyState
                icon={hasScannedWarning || failure ? TriangleAlert : Info}
                title={hasScannedWarning ? "الملف يبدو ممسوحًا ضوئيًا" : "لم نستخرج أي سطر"}
                description={
                  hasScannedWarning
                    ? "تعذر استخراج صفوف من هذا الملف بمساعدة OCR. جرّب نسخة أوضح أو أدخل البيانات يدويًا."
                    : failure ?? "الورقة لا تحتوي على بيانات أو أن الجدول غير واضح."
                }
                action={
                  <div className="flex flex-wrap justify-center gap-2">
                    <button type="button" className="fd-btn fd-btn-primary h-11" onClick={reset}>
                      رفع ملف آخر
                    </button>
                    {multiSheet && (
                      <button
                        type="button"
                        className="fd-btn fd-btn-secondary h-11"
                        onClick={openSheets}
                      >
                        اختيار ورقة أخرى
                      </button>
                    )}
                    <Link
                      href={`/statements/${detail.id}`}
                      className="fd-btn fd-btn-secondary h-11"
                    >
                      إلغاء الاستيراد
                    </Link>
                  </div>
                }
              />
            </section>
          ) : (
            <section className="fd-card overflow-hidden" aria-labelledby="mapping-title">
              <div className="border-b border-[var(--fd-line)] px-5 py-4">
                <h2 id="mapping-title" className="text-sm font-semibold text-[var(--fd-ink)]">
                  مطابقة الأعمدة
                </h2>
                <p className="mt-1 text-[11px] leading-5 text-[var(--fd-ink-subtle)]">
                  اختر العمود المقابل لكل حقل. الحقول المعلّمة بـ{" "}
                  <span className="text-[var(--fd-red-text)]">*</span> مطلوبة.
                </p>
              </div>

              <MappingTable
                headers={headers}
                mapping={mapping}
                suggested={suggested}
                onChange={(field, header) =>
                  setMapping((current) => ({ ...current, [field]: header }))
                }
                disabled={busy}
              />

              {(detail.total_rows ?? 0) > 0 && (
                <p className="flex items-start gap-2 border-t border-[var(--fd-line)] bg-[var(--fd-amber-soft)] px-4 py-2 text-[11px] leading-5 text-[var(--fd-amber-text)]">
                  <TriangleAlert size={14} className="mt-0.5 shrink-0" aria-hidden />
                  إعادة الاستخراج تستبدل الأسطر الحالية. التعديلات اليدوية على الأسطر الحالية
                  ستُفقد.
                </p>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--fd-line)] px-5 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    className="fd-btn fd-btn-ghost h-11"
                    onClick={multiSheet ? openSheets : () => setStage("uploaded")}
                    disabled={busy}
                  >
                    رجوع
                  </button>
                  <button
                    type="button"
                    className="fd-btn fd-btn-ghost h-11"
                    onClick={reset}
                    disabled={busy}
                  >
                    <RotateCcw size={15} aria-hidden />
                    البدء من جديد
                  </button>
                </div>

                <div className="text-end">
                  {(missingRequired.length > 0 || duplicates.length > 0) && (
                    <p
                      id="mapping-gate"
                      className="mb-1 max-w-xs text-[11px] leading-5 text-[var(--fd-red-text)]"
                    >
                      {duplicates.length > 0
                        ? "لا يمكن استخدام العمود نفسه في أكثر من حقل."
                        : `اختر عمودًا لكل من: ${missingRequired.join("، ")}.`}
                    </p>
                  )}
                  <button
                    type="button"
                    className="fd-btn fd-btn-primary h-11"
                    onClick={() => void extractRows()}
                    disabled={
                      busy ||
                      missingRequired.length > 0 ||
                      duplicates.length > 0
                    }
                    aria-describedby={
                      missingRequired.length > 0 || duplicates.length > 0
                        ? "mapping-gate"
                        : undefined
                    }
                    aria-busy={processing}
                  >
                    {processing ? (
                      <LoaderCircle size={16} className="animate-spin" aria-hidden />
                    ) : (
                      <FileSearch size={16} aria-hidden />
                    )}
                    {processing
                      ? "جارٍ استخراج السجلات…"
                      : (detail.total_rows ?? 0) > 0
                        ? "إعادة الاستخراج"
                        : "استخراج السجلات"}
                  </button>
                </div>
              </div>
            </section>
          )}
        </div>
      )}

      {stage === "result" && detail && (
        <div className="space-y-5">
          {detail.status === "failed" ? (
            <section className="fd-card fd-card-pad" aria-labelledby="result-failed-title">
              <h2
                id="result-failed-title"
                tabIndex={-1}
                data-result-heading
                className="flex items-center gap-2 text-sm font-semibold text-[var(--fd-red-text)]"
              >
                <TriangleAlert size={17} aria-hidden />
                تعذر تحليل الملف
              </h2>
              <p className="mt-2 text-[13px] leading-6 text-[var(--fd-red-text)]">
                {failure ?? "تعذر تحليل الملف."}
              </p>
              <p className="mt-1 text-[12px] text-[var(--fd-ink-muted)]">
                لم تُنشأ أي سجلات مالية.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" className="fd-btn fd-btn-primary h-11" onClick={reset}>
                  رفع ملف آخر
                </button>
                <Link
                  href={`/statements/${detail.id}`}
                  className="fd-btn fd-btn-secondary h-11"
                >
                  عرض تفاصيل الاستيراد
                </Link>
              </div>
            </section>
          ) : (detail.total_rows ?? 0) === 0 ? (
            <section className="fd-card fd-card-pad" aria-labelledby="result-empty-title">
              <h2
                id="result-empty-title"
                tabIndex={-1}
                data-result-heading
                className="flex items-center gap-2 text-sm font-semibold text-[var(--fd-amber-text)]"
              >
                <TriangleAlert size={17} aria-hidden />
                {hasScannedWarning ? "الملف يبدو ممسوحًا ضوئيًا" : "لم نستخرج أي سطر"}
              </h2>
              <p className="mt-2 text-[13px] leading-6 text-[var(--fd-ink-muted)]">
                {hasScannedWarning
                  ? "تعذر استخراج صفوف من هذا الملف بمساعدة OCR. جرّب نسخة أوضح أو أدخل البيانات يدويًا."
                  : failure ?? "الورقة لا تحتوي على بيانات أو أن الجدول غير واضح."}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" className="fd-btn fd-btn-primary h-11" onClick={reset}>
                  رفع ملف آخر
                </button>
                {multiSheet && (
                  <button
                    type="button"
                    className="fd-btn fd-btn-secondary h-11"
                    onClick={openSheets}
                  >
                    اختيار ورقة أخرى
                  </button>
                )}
                <Link
                  href={`/statements/${detail.id}`}
                  className="fd-btn fd-btn-secondary h-11"
                >
                  إلغاء الاستيراد
                </Link>
              </div>
            </section>
          ) : (
            <section
              className="fd-card fd-card-pad"
              aria-labelledby="result-title"
              role="status"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2
                    id="result-title"
                    tabIndex={-1}
                    data-result-heading
                    className="flex items-center gap-2 text-sm font-semibold text-[var(--fd-green-text)]"
                  >
                    <CheckCircle2 size={17} aria-hidden />
                    تم استخراج الأسطر
                  </h2>
                  <p className="mt-1 text-[12px] text-[var(--fd-ink-muted)]">
                    <bdi dir="ltr">{detail.source_filename}</bdi>
                    {detail.worksheet_name ? ` · ${detail.worksheet_name}` : ""}
                  </p>
                </div>
                <ImportStatusPill status={detail.status} />
              </div>

              <div className="mt-4">
                <ImportCounts
                  total={detail.total_rows ?? 0}
                  valid={detail.valid_rows ?? 0}
                  invalid={detail.invalid_rows ?? 0}
                  duplicates={detail.duplicate_rows ?? 0}
                  excluded={detail.excluded_rows ?? undefined}
                />
              </div>

              {(detail.invalid_rows ?? 0) > 0 && (
                <p className="mt-3 text-[12px] leading-6 text-[var(--fd-red-text)]">
                  توجد أسطر بأخطاء تحتاج تصحيحًا أو استثناءً قبل التأكيد.
                </p>
              )}

              <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--fd-line)] pt-4">
                <button
                  type="button"
                  className="fd-btn fd-btn-secondary h-11"
                  onClick={() => setStage("mapping")}
                >
                  تعديل مطابقة الأعمدة
                </button>
                <button
                  type="button"
                  className="fd-btn fd-btn-primary h-11"
                  onClick={() => router.push(`/statements/${detail.id}/review`)}
                >
                  فتح المراجعة
                </button>
              </div>
            </section>
          )}
        </div>
      )}

      <Dialog
        open={Boolean(duplicate)}
        onClose={() => {
          if (uploading) return;
          setDuplicate(null);
        }}
        title="هذا الملف مرفوع مسبقًا"
        busy={uploading}
        description={
          <>
            الملف <bdi dir="ltr">{file?.name ?? ""}</bdi> مطابق لكشف سبق رفعه (نفس البصمة).
          </>
        }
      >
        {duplicate?.existingImportId && (
          <Link
            href={`/statements/${duplicate.existingImportId}`}
            className="text-[12px] font-semibold text-[var(--fd-brand)] underline"
          >
            عرض الاستيراد السابق
          </Link>
        )}

        <label className="mt-4 flex min-h-[44px] cursor-pointer items-start gap-2 rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] p-3 text-[12px] leading-6 text-[var(--fd-ink)]">
          <input
            type="checkbox"
            className="mt-1 h-5 w-5 shrink-0 accent-[var(--fd-brand)]"
            checked={duplicateChecked}
            onChange={(event) => setDuplicateChecked(event.target.checked)}
            disabled={uploading}
          />
          رفع نسخة أخرى من الملف
        </label>

        {duplicateChecked && (
          <div className="mt-3">
            <label htmlFor="duplicate-reason" className="fd-label">
              سبب رفع الملف مرة أخرى
            </label>
            <input
              id="duplicate-reason"
              className="fd-input h-11"
              value={duplicateReason}
              onChange={(event) => setDuplicateReason(event.target.value)}
              placeholder="مثال: تصحيح ملف رُفع بالخطأ."
              disabled={uploading}
              aria-describedby="duplicate-reason-hint"
            />
            <p id="duplicate-reason-hint" className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">
              سيُسجَّل السبب في سجل العمليات.
            </p>
          </div>
        )}

        {fileError && (
          <p role="alert" className="mt-3 text-[12px] text-[var(--fd-red-text)]">
            {fileError}
          </p>
        )}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            className="fd-btn fd-btn-secondary h-11"
            onClick={() => setDuplicate(null)}
            disabled={uploading}
            data-autofocus
          >
            إلغاء
          </button>
          <button
            type="button"
            className="fd-btn fd-btn-primary h-11"
            onClick={() => void startUpload(true)}
            disabled={
              uploading ||
              !duplicateChecked ||
              duplicateReason.trim().length === 0
            }
          >
            {uploading ? "جارٍ الرفع…" : "رفع النسخة"}
          </button>
        </div>
      </Dialog>
    </>
  );
}

export default function UploadStatementPage() {
  return (
    <Protected active="/statements">
      <UploadContent />
    </Protected>
  );
}
