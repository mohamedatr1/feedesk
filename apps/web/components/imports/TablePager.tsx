"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { formatNumber } from "@/lib/api";

export function TablePager({
  page,
  pageSize,
  total,
  onPage,
  busy = false,
  itemLabel = "سجل",
}: {
  page: number;
  pageSize: number;
  total: number;
  onPage: (page: number) => void;
  busy?: boolean;
  itemLabel?: string;
}) {
  const totalPages = Math.max(1, Math.ceil(total / Math.max(pageSize, 1)));
  const safePage = Math.min(Math.max(page, 1), totalPages);
  const from = total === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const to = Math.min(safePage * pageSize, total);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--fd-line)] px-5 py-3 text-[11px] text-[var(--fd-ink-subtle)]">
      <span aria-live="polite">
        {total === 0
          ? `لا توجد ${itemLabel}`
          : `عرض ${formatNumber(from)}–${formatNumber(to)} من ${formatNumber(total)}`}
      </span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
          onClick={() => onPage(safePage - 1)}
          disabled={busy || safePage <= 1}
          aria-label="الصفحة السابقة"
        >
          <ChevronRight size={15} aria-hidden />
          السابق
        </button>
        <span className="tabular-nums" aria-hidden>
          {formatNumber(safePage)} / {formatNumber(totalPages)}
        </span>
        <button
          type="button"
          className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
          onClick={() => onPage(safePage + 1)}
          disabled={busy || safePage >= totalPages}
          aria-label="الصفحة التالية"
        >
          التالي
          <ChevronLeft size={15} aria-hidden />
        </button>
      </div>
    </div>
  );
}
