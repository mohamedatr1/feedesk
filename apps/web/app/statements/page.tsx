"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { FileSearch, FileSpreadsheet, FileText, RefreshCw, Upload } from "lucide-react";
import {
  ApiError,
  api,
  formatDateTime,
  formatNumber,
  importErrorMessage,
  type ImportBatchSummary,
  type ImportStatus,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ImportStatusPill, IMPORT_STATUS_OPTIONS } from "@/components/imports/ImportStatusPill";
import { IssueList } from "@/components/imports/IssueList";

const PAGE_SIZE = 20;

function shortId(value: string | null | undefined): string {
  if (!value) return "—";
  return value.slice(0, 8);
}

function StatementsContent() {
  const { user, settings } = useSession();
  const isAdmin = user.role === "admin";
  const [items, setItems] = useState<ImportBatchSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<ImportStatus | "">("");
  const [actors, setActors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [summary, setSummary] = useState<{
    total: number;
    review: number;
    lastUpload: string | null;
  } | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    api
      .listImports({ page, page_size: PAGE_SIZE, status })
      .then((data) => {
        if (!mounted) return;
        setItems(data.items ?? []);
        setTotal(data.total ?? 0);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 401) {
          setError("انتهت الجلسة. أعد تسجيل الدخول للمتابعة.");
        } else if (err instanceof ApiError && err.status === 403) {
          setError("لا تملك صلاحية عرض سجل الاستيراد. تواصل مع مدير النظام.");
        } else {
          setError(err instanceof ApiError ? err.messageAr : "تعذر تحميل سجل الاستيراد.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [page, status, reloadKey]);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      api.listImports({ page: 1, page_size: 1 }),
      api.listImports({ page: 1, page_size: 1, status: "review_required" }),
      api.listImports({ page: 1, page_size: 1, status: "ready_to_confirm" }),
    ])
      .then(([all, review, ready]) => {
        if (!mounted) return;
        setSummary({
          total: all.total ?? 0,
          review: (review.total ?? 0) + (ready.total ?? 0),
          lastUpload: all.items?.[0]?.created_at ?? null,
        });
      })
      .catch(() => {
        if (mounted) setSummary(null);
      });
    return () => {
      mounted = false;
    };
  }, [reloadKey]);

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

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <PageHeader
        title="كشوف الأقساط"
        subtitle="رفع الكشوف، مراجعة السجلات المستخرجة، ثم تأكيد الاستيراد."
        action={
          <Link href="/statements/upload" className="fd-btn fd-btn-primary h-11">
            <Upload size={16} aria-hidden />
            رفع كشف جديد
          </Link>
        }
      />

      <p className="mb-4 text-[12px] text-[var(--fd-ink-muted)]" aria-live="polite">
        {summary === null
          ? loading
            ? "— · — · —"
            : null
          : summary.total === 0
            ? null
            : (
                <>
                  الكشوف: {formatNumber(summary.total)}
                  {summary.review > 0 && ` · بانتظار المراجعة: ${formatNumber(summary.review)}`}
                  {summary.lastUpload && (
                    <>
                      {" · آخر رفع "}
                      <bdi dir="ltr">
                        {formatDateTime(summary.lastUpload, {
                          locale: settings?.locale,
                          timeZone: settings?.timezone,
                        })}
                      </bdi>
                    </>
                  )}
                </>
              )}
      </p>

      <section className="fd-card overflow-hidden" aria-labelledby="imports-title">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--fd-line)] px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="h-4 w-1 rounded-full bg-[var(--fd-brand)]" aria-hidden />
            <h2 id="imports-title" className="text-sm font-semibold text-[var(--fd-ink)]">
              سجل الاستيراد
            </h2>
            {!loading && (
              <span className="text-[11px] text-[var(--fd-ink-subtle)]">
                ({formatNumber(total)})
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="status-filter" className="text-[12px] text-[var(--fd-ink-muted)]">
              الحالة
            </label>
            <select
              id="status-filter"
              className="fd-input h-11 w-[170px]"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value as ImportStatus | "");
                setPage(1);
              }}
            >
              {IMPORT_STATUS_OPTIONS.map((option) => (
                <option key={option.value || "all"} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={reload}
              disabled={loading}
              className="fd-btn fd-btn-ghost h-11 px-3 text-[12px]"
            >
              <RefreshCw size={14} aria-hidden />
              تحديث
            </button>
          </div>
        </div>

        {error ? (
          <div role="alert" className="px-5 py-8 text-center">
            <p className="text-[13px] text-[var(--fd-red-text)]">{error}</p>
            <button type="button" onClick={reload} className="fd-btn fd-btn-secondary mt-4 h-11">
              إعادة المحاولة
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="fd-table min-w-0 xl:min-w-[980px]" aria-busy={loading}>
              <caption className="sr-only">
                سجل عمليات استيراد الكشوف. الأحدث أولًا، مع الحالة وعدد الصفوف والملاحظات.
              </caption>
              <thead>
                <tr>
                  <th scope="col">الملف</th>
                  <th scope="col" className="hidden sm:table-cell">الحالة</th>
                  <th scope="col" className="hidden sm:table-cell">الصفوف</th>
                  <th scope="col" className="hidden xl:table-cell">الملاحظات</th>
                  <th scope="col" className="hidden xl:table-cell">تاريخ الرفع</th>
                  <th scope="col" className="hidden xl:table-cell">رفع بواسطة</th>
                  <th scope="col" className="w-[1%] whitespace-nowrap">
                    <span className="sr-only">الإجراءات</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading &&
                  Array.from({ length: 4 }).map((_, index) => (
                    <tr key={`skeleton-${index}`}>
                      <td colSpan={7}>
                        <div className="fd-skeleton h-6 w-full" />
                      </td>
                    </tr>
                  ))}

                {!loading &&
                  items.map((item) => {
                    const reviewable =
                      item.status === "review_required" || item.status === "ready_to_confirm";
                    const failure = importErrorMessage(item.error_summary);
                    const uploaderName =
                      item.uploaded_by_name ??
                      (item.uploaded_by && item.uploaded_by === user.id
                        ? user.username
                        : item.uploaded_by
                          ? actors[item.uploaded_by] ?? shortId(item.uploaded_by)
                          : "—");
                    const FileIcon =
                      item.file_type === "xlsx" ? FileSpreadsheet : FileText;
                    return (
                      <tr key={item.id} className="hover:bg-[var(--fd-surface-alt)]">
                        <th
                          scope="row"
                          className="bg-transparent align-top text-[13px] font-normal text-[var(--fd-ink)]"
                        >
                          <Link
                            href={`/statements/${item.id}`}
                            className="flex min-w-0 items-center gap-2 font-medium text-[var(--fd-ink)] hover:text-[var(--fd-brand)] hover:underline"
                          >
                            <FileIcon
                              size={16}
                              className="shrink-0 text-[var(--fd-ink-subtle)]"
                              aria-hidden
                            />
                            <bdi dir="auto" className="min-w-0 truncate">
                              {item.source_filename}
                            </bdi>
                          </Link>
                          <p className="mt-0.5 text-[11px] text-[var(--fd-ink-subtle)]">
                            {item.file_type.toUpperCase()}
                            {item.worksheet_name ? ` · ${item.worksheet_name}` : ""}
                          </p>
                          <p className="mt-1 sm:hidden">
                            <ImportStatusPill status={item.status} />
                          </p>
                        </th>
                        <td className="hidden align-top sm:table-cell">
                          <ImportStatusPill status={item.status} />
                          {failure && item.status === "failed" && (
                            <p className="mt-1 max-w-[200px] truncate text-[11px] text-[var(--fd-red-text)]">
                              {failure}
                            </p>
                          )}
                          {!failure && (item.invalid_rows ?? 0) > 0 && (
                            <p className="mt-1 text-[11px] text-[var(--fd-red-text)]">
                              الأخطاء: {formatNumber(item.invalid_rows)}
                            </p>
                          )}
                        </td>
                        <td className="hidden whitespace-nowrap align-top sm:table-cell">
                          <p className="font-semibold tabular-nums text-[var(--fd-ink)]">
                            {formatNumber(item.total_rows)}
                          </p>
                          <p className="text-[11px] text-[var(--fd-ink-subtle)]">
                            صالح {formatNumber(item.valid_rows)} · خطأ{" "}
                            {formatNumber(item.invalid_rows)} · مكرر{" "}
                            {formatNumber(item.duplicate_rows)}
                            {item.excluded_rows != null &&
                              ` · مستثنى ${formatNumber(item.excluded_rows)}`}
                          </p>
                        </td>
                        <td className="hidden max-w-[230px] align-top xl:table-cell">
                          {(item.warnings ?? []).length > 0 ? (
                            <details>
                              <summary className="cursor-pointer text-[12px] font-medium text-[var(--fd-amber-text)]">
                                تحذيرات الملف: {formatNumber((item.warnings ?? []).length)}
                              </summary>
                              <IssueList issues={item.warnings ?? []} className="mt-2" />
                            </details>
                          ) : (
                            <span className="text-[12px] text-[var(--fd-ink-subtle)]">—</span>
                          )}
                        </td>
                        <td className="hidden whitespace-nowrap align-top tabular-nums xl:table-cell">
                          <bdi dir="ltr">
                            {formatDateTime(item.created_at, {
                              locale: settings?.locale,
                              timeZone: settings?.timezone,
                            })}
                          </bdi>
                        </td>
                        <td className="hidden whitespace-nowrap align-top text-[12px] xl:table-cell">
                          <bdi dir="ltr" title={item.uploaded_by ?? undefined}>
                            {uploaderName}
                          </bdi>
                        </td>
                        <td className="align-top">
                          {reviewable ? (
                            <Link
                              href={`/statements/${item.id}/review`}
                              className="fd-btn fd-btn-primary h-11 px-3 text-[12px]"
                              aria-label={`مراجعة كشف ${item.source_filename}`}
                            >
                              <FileSearch size={15} aria-hidden />
                              <span className="hidden sm:inline">مراجعة</span>
                            </Link>
                          ) : item.status === "uploaded" ? (
                            <Link
                              href={`/statements/upload?import=${item.id}`}
                              className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                              aria-label={`متابعة كشف ${item.source_filename}`}
                            >
                              <Upload size={15} aria-hidden />
                              <span className="hidden sm:inline">متابعة</span>
                            </Link>
                          ) : item.status === "processing" ? (
                            <span className="text-[11px] text-[var(--fd-ink-subtle)]">
                              جارٍ المعالجة…
                            </span>
                          ) : (
                            <Link
                              href={`/statements/${item.id}`}
                              className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                              aria-label={`عرض كشف ${item.source_filename}`}
                            >
                              <FileText size={15} aria-hidden />
                              <span className="hidden sm:inline">عرض</span>
                            </Link>
                          )}
                        </td>
                      </tr>
                    );
                  })}

                {!loading && items.length === 0 && (
                  <tr>
                    <td colSpan={7}>
                      <EmptyState
                        icon={FileText}
                        title={status ? "لا توجد كشوف بهذه الحالة" : "لا توجد كشوف بعد"}
                        description={
                          status
                            ? "جرّب حالة أخرى."
                            : "ارفع كشف Excel أو PDF لاستخراج السجلات المالية ومراجعتها قبل التأكيد."
                        }
                        action={
                          status ? (
                            <button
                              type="button"
                              className="fd-btn fd-btn-secondary h-11"
                              onClick={() => {
                                setStatus("");
                                setPage(1);
                              }}
                            >
                              عرض كل الكشوف
                            </button>
                          ) : (
                            <Link
                              href="/statements/upload"
                              className="fd-btn fd-btn-secondary h-11"
                            >
                              <Upload size={16} aria-hidden />
                              رفع كشف جديد
                            </Link>
                          )
                        }
                      />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {!error && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--fd-line)] px-5 py-3 text-[11px] text-[var(--fd-ink-subtle)]">
            <span aria-live="polite">
              {loading
                ? "جارٍ تحميل السجل…"
                : total === 0
                  ? "لا توجد سجلات"
                  : `الصفحة ${formatNumber(page)} من ${formatNumber(totalPages)}`}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={loading || page <= 1}
              >
                السابق
              </button>
              <button
                type="button"
                className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={loading || page >= totalPages}
              >
                التالي
              </button>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

export default function StatementsPage() {
  return (
    <Protected active="/statements">
      <StatementsContent />
    </Protected>
  );
}
