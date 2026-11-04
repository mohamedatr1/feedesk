import { Ban, RotateCcw, TriangleAlert } from "lucide-react";
import { formatNumber } from "@/lib/api";

/**
 * The bulk bar for the current page. It stays visible while the import is
 * reviewable and disables actions rather than hiding them, so the available
 * operations are always discoverable.
 */
export function BulkExclusionBar({
  selectedCount,
  pageCount,
  invalidCount,
  busy,
  disabled,
  onClear,
  onExcludeSelected,
  onRestoreSelected,
  onExcludeInvalid,
}: {
  selectedCount: number;
  pageCount: number;
  invalidCount: number;
  busy: boolean;
  disabled: boolean;
  onClear: () => void;
  onExcludeSelected: () => void;
  onRestoreSelected: () => void;
  onExcludeInvalid: () => void;
}) {
  return (
    <div
      role="group"
      aria-label="إجراءات جماعية على الأسطر"
      className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--fd-line)] px-5 py-3"
    >
      <div className="flex flex-wrap items-center gap-2 text-[12px] text-[var(--fd-ink-muted)]">
        <span>
          المحدد{" "}
          <bdi className="font-semibold tabular-nums text-[var(--fd-ink)]">
            {formatNumber(selectedCount)}
          </bdi>{" "}
          من {formatNumber(pageCount)} في هذه الصفحة
        </span>
        {selectedCount > 0 && (
          <button
            type="button"
            onClick={onClear}
            disabled={busy}
            className="fd-btn fd-btn-ghost h-11 px-2 text-[12px]"
          >
            مسح التحديد
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onExcludeSelected}
          disabled={disabled || selectedCount === 0}
          className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
        >
          <Ban size={15} aria-hidden />
          استثناء المحدد
        </button>
        <button
          type="button"
          onClick={onRestoreSelected}
          disabled={disabled || selectedCount === 0}
          className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
        >
          <RotateCcw size={15} aria-hidden />
          استعادة المحدد
        </button>
        <button
          type="button"
          onClick={onExcludeInvalid}
          disabled={disabled || invalidCount === 0}
          className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
          title="يشمل كل سطر به أخطاء في هذا الكشف"
        >
          <TriangleAlert size={15} aria-hidden />
          استثناء الصفوف غير الصالحة
          <bdi className="tabular-nums">({formatNumber(invalidCount)})</bdi>
        </button>
      </div>
    </div>
  );
}
