"use client";

import Link from "next/link";
import { Check, FileCheck, FileSpreadsheet, RefreshCw } from "lucide-react";
import { formatDateTime, formatNumber } from "@/lib/api";
import type { ImportBatchSummary } from "@/lib/api";
import { EmptyState } from "@/components/EmptyState";

export function ConfirmedImportPicker({
  imports,
  total,
  loading,
  error,
  selectedId,
  onSelect,
  onRetry,
  locale,
  timeZone,
}: {
  imports: ImportBatchSummary[];
  total: number | null;
  loading: boolean;
  error: string | null;
  selectedId: string;
  onSelect: (id: string) => void;
  onRetry: () => void;
  locale?: string | null;
  timeZone?: string | null;
}) {
  if (error) {
    return (
      <div
        role="alert"
        className="rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] p-4 text-[12px] text-[var(--fd-red-text)]"
      >
        <p>تعذر تحميل الكشوف المؤكدة.</p>
        <p className="mt-1 text-[11px]">{error}</p>
        <button
          type="button"
          onClick={onRetry}
          className="fd-btn fd-btn-secondary mt-3 h-11 px-3 text-[12px]"
        >
          <RefreshCw size={14} aria-hidden />
          إعادة المحاولة
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-2" aria-busy="true">
        <div className="fd-skeleton h-16 w-full" />
        <div className="fd-skeleton h-16 w-full" />
      </div>
    );
  }

  if (imports.length === 0) {
    return (
      <div className="rounded-[var(--fd-radius-control)] border border-[var(--fd-line)]">
        <EmptyState
          icon={FileCheck}
          title="لا يوجد كشف مؤكد"
          description="تُبنى الحملات من كشوف مؤكدة فقط. أكّد كشفًا أولًا."
          action={
            <Link href="/statements" className="fd-btn fd-btn-secondary h-11">
              عرض الكشوف
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div>
      <fieldset>
        <legend className="sr-only">الكشف المؤكد</legend>
        <div className="space-y-2">
          {imports.map((item) => {
            const selected = item.id === selectedId;
            const currencies = Object.keys(item.totals_by_currency ?? {}).filter(Boolean);
            return (
              <label
                key={item.id}
                className={`flex min-h-[64px] cursor-pointer items-start gap-3 rounded-[var(--fd-radius-control)] border p-3 transition ${
                  selected
                    ? "border-2 border-[var(--fd-brand)] bg-[var(--fd-brand-soft)]"
                    : "border-[var(--fd-line)] hover:bg-[var(--fd-surface-alt)]"
                }`}
              >
                <input
                  type="radio"
                  name="source_import_id"
                  value={item.id}
                  checked={selected}
                  onChange={() => onSelect(item.id)}
                  className="mt-1 h-5 w-5 shrink-0 accent-[var(--fd-brand)]"
                  required
                />
                <span className="min-w-0 flex-1">
                  <span className="flex items-start justify-between gap-2">
                    <bdi
                      dir="auto"
                      className="flex min-w-0 items-center gap-2 truncate text-[13px] font-medium text-[var(--fd-ink)]"
                    >
                      <FileSpreadsheet
                        size={15}
                        className="shrink-0 text-[var(--fd-ink-subtle)]"
                        aria-hidden
                      />
                      <span className="truncate">{item.source_filename}</span>
                    </bdi>
                    {selected && (
                      <Check
                        size={16}
                        className="shrink-0 text-[var(--fd-brand)]"
                        aria-hidden
                      />
                    )}
                  </span>
                  <span className="mt-0.5 block text-[11px] text-[var(--fd-ink-subtle)]">
                    مؤكد{" "}
                    <bdi dir="ltr">
                      {formatDateTime(item.confirmed_at ?? item.created_at, {
                        locale,
                        timeZone,
                      })}
                    </bdi>{" "}
                    · {formatNumber(item.total_rows)} أسطر
                  </span>
                  {currencies.length > 0 && (
                    <span className="mt-1 flex flex-wrap gap-1">
                      {currencies.sort().map((currency) => (
                        <span
                          key={currency}
                          className="rounded-full bg-[var(--fd-surface-alt)] px-2 py-0.5 text-[10px] text-[var(--fd-ink-muted)]"
                          dir="ltr"
                          lang="en"
                        >
                          {currency}
                        </span>
                      ))}
                    </span>
                  )}
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <Link
          href="/statements"
          className="inline-flex min-h-11 items-center text-[12px] font-medium text-[var(--fd-brand)] hover:underline"
        >
          عرض كل الكشوف المؤكدة
        </Link>
        {total != null && total > imports.length && (
          <span className="text-[11px] text-[var(--fd-ink-subtle)]">
            تُعرض أحدث {formatNumber(imports.length)} من {formatNumber(total)} كشفًا مؤكدًا.
          </span>
        )}
      </div>
    </div>
  );
}
