"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  Copy,
  ExternalLink,
  FileSearch,
  FileText,
  TriangleAlert,
  XCircle,
} from "lucide-react";
import {
  ApiError,
  IMPORT_FIELD_LABELS,
  MAPPING_FIELDS,
  api,
  formatDateTime,
  formatNumber,
  importErrorMessage,
  importSourceFileUrl,
  type ImportDetail,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ImportCounts } from "@/components/imports/ImportCounts";
import { ImportStatusPill } from "@/components/imports/ImportStatusPill";
import { IssueList } from "@/components/imports/IssueList";
import { CurrencyTotals } from "@/components/imports/CurrencyTotals";

const CANCELABLE = new Set(["uploaded", "review_required", "ready_to_confirm"]);

const ERROR_CODE_LABELS: Record<string, string> = {
  MISSING_GUARDIAN: "اسم ولي الأمر مفقود",
  MISSING_BALANCE: "الرصيد المتبقي مفقود",
  NEGATIVE_BALANCE: "الرصيد المتبقي سالب",
  MISSING_CURRENCY: "العملة مفقودة",
  AMBIGUOUS_MONEY: "قيمة مالية غير واضحة",
  DUPLICATE_ROW: "صف مكرر",
};

function shortId(value: string | null | undefined): string {
  if (!value) return "—";
  return value.slice(0, 8);
}

function DetailContent() {
  const params = useParams<{ id: string }>();
  const importId = typeof params.id === "string" ? params.id : "";
  const { user, settings } = useSession();
  const isAdmin = user.role === "admin";

  const [detail, setDetail] = useState<ImportDetail | null>(null);
  const [actors, setActors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);

  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [confirmedBanner, setConfirmedBanner] = useState(false);
  const [copied, setCopied] = useState(false);
  const bannerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setConfirmedBanner(
      new URLSearchParams(window.location.search).get("confirmed") === "1",
    );
  }, [importId]);

  useEffect(() => {
    if (confirmedBanner && detail) bannerRef.current?.focus();
  }, [confirmedBanner, detail]);

  useEffect(() => {
    if (!importId) return;
    let mounted = true;
    setLoading(true);
    setError(null);

    api
      .getImport(importId)
      .then((data) => {
        if (mounted) setDetail(data);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 404) {
          setError("لم نجد هذا الكشف. قد يكون الرابط قديمًا أو أن الكشف غير متاح لحسابك.");
        } else if (err instanceof ApiError && err.status === 403) {
          setError("لا تملك صلاحية عرض هذا الكشف.");
        } else {
          setError(err instanceof ApiError ? err.messageAr : "تعذر تحميل تفاصيل الاستيراد.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [importId, version]);

  useEffect(() => {
    if (!isAdmin) return;
    let mounted = true;
    api
      .listUsers()
      .then((users) => {
        if (!mounted) return;
        setActors(Object.fromEntries(users.map((item) => [item.id, item.username])));
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, [isAdmin]);

  async function cancelImport() {
    setCancelling(true);
    setCancelError(null);
    try {
      const updated = await api.cancelImport(importId);
      setDetail(updated);
      setCancelOpen(false);
      setNotice("تم إلغاء الاستيراد. لن تُثبَّت أي أرصدة من هذا الكشف.");
    } catch (err) {
      setCancelError(
        err instanceof ApiError ? err.messageAr : "تعذر إلغاء الاستيراد. حاول مرة أخرى.",
      );
    } finally {
      setCancelling(false);
    }
  }

  async function copyId() {
    if (!detail) return;
    try {
      await navigator.clipboard.writeText(detail.id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  if (loading && !detail) {
    return (
      <>
        <PageHeader title="تفاصيل الاستيراد" subtitle="جارٍ تحميل البيانات…" />
        <div className="fd-card fd-card-pad space-y-3">
          <div className="fd-skeleton h-8 w-64" />
          <div className="fd-skeleton h-24 w-full" />
          <div className="fd-skeleton h-24 w-full" />
        </div>
      </>
    );
  }

  if (error || !detail) {
    return (
      <>
        <PageHeader title="تفاصيل الاستيراد" subtitle="ملف الكشف، الأعداد، والملاحظات." />
        <div className="fd-card">
          <div className="px-6 py-12 text-center">
            <p role="alert" className="text-sm font-semibold text-[var(--fd-red-text)]">
              {error ?? "تعذر تحميل تفاصيل الاستيراد."}
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              <button
                type="button"
                className="fd-btn fd-btn-secondary h-11"
                onClick={() => setVersion((value) => value + 1)}
              >
                إعادة المحاولة
              </button>
              <Link href="/statements" className="fd-btn fd-btn-primary h-11">
                العودة إلى السجل
              </Link>
            </div>
          </div>
        </div>
      </>
    );
  }

  const reviewable =
    detail.status === "review_required" || detail.status === "ready_to_confirm";
  const sourceUrl = importSourceFileUrl(detail.source_file_id);
  const mappingEntries = Object.entries(detail.column_mapping ?? {}).filter(
    ([, header]) => Boolean(header),
  );
  const uploader =
    detail.uploaded_by_name ??
    (detail.uploaded_by && detail.uploaded_by === user.id
      ? user.username
      : detail.uploaded_by
        ? actors[detail.uploaded_by] ?? shortId(detail.uploaded_by)
        : "—");
  const confirmer =
    detail.confirmed_by && detail.confirmed_by === user.id
      ? user.username
      : detail.confirmed_by
        ? actors[detail.confirmed_by] ?? shortId(detail.confirmed_by)
        : "—";
  const totalRows = detail.total_rows ?? 0;
  const excludedRows = detail.excluded_rows ?? null;
  const confirmedRows = Math.max(
    totalRows - (excludedRows ?? 0) - (detail.invalid_rows ?? 0),
    0,
  );

  return (
    <>
      <nav aria-label="مسار التصفح" className="mb-3 flex flex-wrap items-center gap-1.5 text-[11px] text-[var(--fd-ink-subtle)]">
        <Link href="/statements" className="hover:underline">
          كشوف الأقساط
        </Link>
        <span aria-hidden>/</span>
        <span aria-current="page" className="max-w-[320px] truncate text-[var(--fd-ink-muted)]">
          <bdi dir="ltr">{detail.source_filename}</bdi>
        </span>
      </nav>

      <PageHeader
        title={detail.source_filename}
        subtitle={`${detail.worksheet_name ?? (detail.file_type === "pdf" ? "ملف PDF" : "بدون ورقة")} · رُفع ${formatDateTime(detail.created_at, {
          locale: settings?.locale,
          timeZone: settings?.timezone,
        })} · بواسطة ${uploader}`}
        action={
          <div className="flex flex-wrap items-center gap-2">
            {sourceUrl && (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="fd-btn fd-btn-secondary h-11"
                aria-label="عرض الملف الأصلي (يفتح في تبويب جديد)"
              >
                <ExternalLink size={15} aria-hidden />
                عرض الملف الأصلي
              </a>
            )}
            {reviewable && (
              <Link
                href={`/statements/${detail.id}/review`}
                className="fd-btn fd-btn-primary h-11"
              >
                <FileSearch size={16} aria-hidden />
                مراجعة الأسطر
              </Link>
            )}
            {detail.status === "uploaded" && (
              <Link
                href={`/statements/upload?import=${detail.id}`}
                className="fd-btn fd-btn-primary h-11"
              >
                اختيار الورقة
              </Link>
            )}
            {detail.status === "failed" && (
              <Link href="/statements/upload" className="fd-btn fd-btn-primary h-11">
                رفع ملف آخر
              </Link>
            )}
          </div>
        }
      />

      {confirmedBanner && detail.status === "confirmed" && (
        <div
          ref={bannerRef}
          tabIndex={-1}
          role="status"
          className="mb-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-green-soft)] px-3 py-2 text-[12px] text-[var(--fd-green-text)] outline-none"
        >
          تم تأكيد الاستيراد. الأسطر المؤكدة: {formatNumber(confirmedRows)}. السجلات للعرض فقط.
        </div>
      )}

      {notice && (
        <p
          role="status"
          className="mb-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-green-soft)] px-3 py-2 text-[12px] text-[var(--fd-green-text)]"
        >
          {notice}
        </p>
      )}

      <section className="fd-card mb-5 overflow-hidden" aria-labelledby="detail-summary-title">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--fd-line)] px-5 py-4">
          <div className="min-w-0">
            <h2
              id="detail-summary-title"
              className="flex items-center gap-2 text-sm font-semibold text-[var(--fd-ink)]"
            >
              <FileText size={16} className="shrink-0 text-[var(--fd-brand)]" aria-hidden />
              <bdi dir="ltr" className="truncate">
                {detail.source_filename}
              </bdi>
            </h2>
            <p className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">
              {detail.file_type.toUpperCase()}
              {detail.worksheet_name ? ` · ورقة: ${detail.worksheet_name}` : ""}
              {(detail.available_sheets ?? []).length > 1
                ? ` · ${(detail.available_sheets ?? []).length} أوراق متاحة`
                : ""}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ImportStatusPill status={detail.status} />
            {CANCELABLE.has(detail.status) && (
              <button
                type="button"
                className="fd-btn fd-btn-ghost h-11 px-3 text-[12px] text-[var(--fd-red-text)]"
                onClick={() => {
                  setCancelError(null);
                  setCancelOpen(true);
                }}
              >
                <XCircle size={15} aria-hidden />
                إلغاء الاستيراد
              </button>
            )}
          </div>
        </div>

        <div className="px-5 py-4">
          <ImportCounts
            total={totalRows}
            valid={detail.valid_rows ?? 0}
            invalid={detail.invalid_rows ?? 0}
            duplicates={detail.duplicate_rows ?? 0}
            excluded={excludedRows ?? undefined}
          />

          {detail.totals_by_currency &&
            Object.keys(detail.totals_by_currency).length > 0 && (
            <div className="mt-4">
              <h3 className="mb-1 text-[11px] font-medium text-[var(--fd-ink-muted)]">
                الإجماليات حسب العملة
              </h3>
              <CurrencyTotals totals={detail.totals_by_currency} />
            </div>
          )}

          {(detail.warnings ?? []).length === 0 && !detail.error_summary && (
            <p className="mt-3 text-[12px] text-[var(--fd-ink-subtle)]">
              لا توجد تحذيرات على هذا الكشف.
            </p>
          )}

          <dl className="mt-5 grid gap-x-6 gap-y-3 text-[12px] sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <dt className="text-[var(--fd-ink-subtle)]">رفع بواسطة</dt>
              <dd className="mt-0.5 font-medium text-[var(--fd-ink)]">
                <bdi dir="ltr" title={detail.uploaded_by ?? undefined}>
                  {uploader}
                </bdi>
              </dd>
            </div>
            <div>
              <dt className="text-[var(--fd-ink-subtle)]">تاريخ الرفع</dt>
              <dd className="mt-0.5 tabular-nums text-[var(--fd-ink)]">
                <bdi dir="ltr">
                  {formatDateTime(detail.created_at, {
                    locale: settings?.locale,
                    timeZone: settings?.timezone,
                  })}
                </bdi>
              </dd>
            </div>
            <div>
              <dt className="text-[var(--fd-ink-subtle)]">تاريخ التأكيد</dt>
              <dd className="mt-0.5 tabular-nums text-[var(--fd-ink)]">
                {detail.confirmed_at ? (
                  <bdi dir="ltr">
                    {formatDateTime(detail.confirmed_at, {
                      locale: settings?.locale,
                      timeZone: settings?.timezone,
                    })}
                  </bdi>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt className="text-[var(--fd-ink-subtle)]">أكّد بواسطة</dt>
              <dd className="mt-0.5 font-medium text-[var(--fd-ink)]">
                {detail.confirmed_by ? (
                  <bdi dir="ltr" title={detail.confirmed_by}>
                    {confirmer}
                  </bdi>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt className="text-[var(--fd-ink-subtle)]">المعرّف</dt>
              <dd className="mt-0.5 flex items-center gap-2 font-mono text-[11px] text-[var(--fd-ink-muted)]">
                <bdi dir="ltr" title={detail.id}>
                  {detail.id.slice(0, 8)}
                </bdi>
                <button
                  type="button"
                  className="fd-btn fd-btn-ghost h-11 px-2 text-[11px]"
                  onClick={() => void copyId()}
                  aria-label="نسخ معرّف الدفعة"
                >
                  <Copy size={13} aria-hidden />
                  {copied ? "نُسخ" : "نسخ"}
                </button>
              </dd>
            </div>
            {detail.cancelled_at && (
              <div>
                <dt className="text-[var(--fd-ink-subtle)]">تاريخ الإلغاء</dt>
                <dd className="mt-0.5 tabular-nums text-[var(--fd-ink)]">
                  <bdi dir="ltr">
                    {formatDateTime(detail.cancelled_at, {
                      locale: settings?.locale,
                      timeZone: settings?.timezone,
                    })}
                  </bdi>
                </dd>
              </div>
            )}
            {detail.updated_at && (
              <div>
                <dt className="text-[var(--fd-ink-subtle)]">آخر تحديث</dt>
                <dd className="mt-0.5 tabular-nums text-[var(--fd-ink)]">
                  <bdi dir="ltr">
                    {formatDateTime(detail.updated_at, {
                      locale: settings?.locale,
                      timeZone: settings?.timezone,
                    })}
                  </bdi>
                </dd>
              </div>
            )}
            <div>
              <dt className="text-[var(--fd-ink-subtle)]">الملف المصدر</dt>
              <dd className="mt-0.5">
                {sourceUrl ? (
                  <a
                    href={sourceUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex min-h-[44px] items-center gap-1 font-medium text-[var(--fd-brand)] hover:underline"
                    aria-label="عرض الملف الأصلي (يفتح في تبويب جديد)"
                  >
                    <ExternalLink size={14} aria-hidden />
                    عرض الملف
                  </a>
                ) : (
                  <span className="text-[var(--fd-ink-subtle)]">—</span>
                )}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      {((detail.warnings ?? []).length > 0 ||
        detail.error_summary ||
        detail.duplicate_reason) && (
        <section className="fd-card fd-card-pad mb-5" aria-labelledby="detail-warnings-title">
          <h2 id="detail-warnings-title" className="text-sm font-semibold text-[var(--fd-ink)]">
            الحالة والتحذيرات
          </h2>

          {(detail.warnings ?? []).length > 0 && (
            <IssueList issues={detail.warnings ?? []} className="mt-3" showCodes />
          )}

          {detail.error_summary && (
            <div className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] leading-6 text-[var(--fd-red-text)]">
              <p className="font-semibold">سبب الفشل</p>
              <p className="mt-1">
                {importErrorMessage(detail.error_summary) ?? "تعذر تحليل الملف."}
              </p>
              {typeof detail.error_summary === "object" &&
                !detail.error_summary.message_ar &&
                Object.keys(detail.error_summary.by_code ?? {}).length > 0 && (
                  <ul className="mt-1.5 flex flex-wrap gap-1.5">
                    {Object.entries(detail.error_summary.by_code ?? {}).map(
                      ([code, count]) => (
                        <li
                          key={code}
                          className="rounded-full bg-[var(--fd-surface)] px-2 py-0.5 text-[11px]"
                        >
                          {ERROR_CODE_LABELS[code] ?? code}: {formatNumber(count)}
                        </li>
                      ),
                    )}
                  </ul>
                )}
              <p className="mt-1 font-medium">لم تُنشأ أي سجلات مالية.</p>
            </div>
          )}

          {detail.duplicate_reason && (
            <p className="mt-3 flex items-start gap-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] px-3 py-2 text-[12px] leading-6 text-[var(--fd-amber-text)]">
              <TriangleAlert size={15} className="mt-1 shrink-0" aria-hidden />
              سبب رفع نسخة مكررة: {detail.duplicate_reason}
            </p>
          )}
        </section>
      )}

      {mappingEntries.length > 0 && (
        <details
          className="fd-card overflow-hidden"
          open={detail.status !== "confirmed"}
        >
          <summary className="cursor-pointer list-none border-b border-[var(--fd-line)] px-5 py-4 text-sm font-semibold text-[var(--fd-ink)]">
            مطابقة الأعمدة المستخدمة
          </summary>
          <div className="overflow-x-auto">
            <table className="fd-table min-w-[480px]">
              <caption className="sr-only">ربط حقول النظام بأعمدة الملف المصدر</caption>
              <thead>
                <tr>
                  <th scope="col">الحقل</th>
                  <th scope="col">العمود في الملف</th>
                </tr>
              </thead>
              <tbody>
                {MAPPING_FIELDS.map((field) => (
                  <tr key={field}>
                    <td className="font-medium text-[var(--fd-ink)]">
                      {IMPORT_FIELD_LABELS[field] ?? field}
                    </td>
                    <td>
                      {detail.column_mapping?.[field] ? (
                        <bdi>{detail.column_mapping[field]}</bdi>
                      ) : (
                        <span className="text-[var(--fd-ink-subtle)]">— (غير مطابق)</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}

      <ConfirmDialog
        open={cancelOpen}
        title="إلغاء الاستيراد؟"
        description={
          <>
            لن تُنشأ أي سجلات مالية. سيبقى الكشف في السجل بحالة «ملغى». سيتم إلغاء استيراد{" "}
            <span className="font-semibold text-[var(--fd-ink)]">
              <bdi dir="ltr">{detail.source_filename}</bdi>
            </span>
            .
          </>
        }
        confirmLabel="إلغاء الاستيراد"
        busyLabel="جارٍ الإلغاء…"
        busy={cancelling}
        error={cancelError}
        onConfirm={() => void cancelImport()}
        onClose={() => {
          if (cancelling) return;
          setCancelOpen(false);
          setCancelError(null);
        }}
      />
    </>
  );
}

export default function StatementDetailPage() {
  return (
    <Protected active="/statements">
      <DetailContent />
    </Protected>
  );
}
