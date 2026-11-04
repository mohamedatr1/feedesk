import { TriangleAlert } from "lucide-react";
import { formatNumber, type GuardianCandidateRow } from "@/lib/api";
import { rowsNeedResolution } from "@/components/imports/guardian-format";

/**
 * Shown after confirm is refused with AMBIGUOUS_GUARDIAN. It states plainly
 * that confirmation did not happen and gives each affected row a way back into
 * the ledger (or a name search when the row is on another page).
 */
export function AmbiguousGuardianNotice({
  ids,
  rows,
  onReveal,
  onResolve,
  onDismiss,
}: {
  ids: string[];
  rows: GuardianCandidateRow[];
  onReveal: (rowId: string, guardianName: string) => void;
  onResolve: (row: GuardianCandidateRow) => void;
  onDismiss: () => void;
}) {
  if (ids.length === 0) return null;

  return (
    <section
      id="ambiguous-guardian-notice"
      tabIndex={-1}
      role="alert"
      aria-labelledby="ambiguous-guardian-title"
      className="mb-4 rounded-[var(--fd-radius-card)] border border-[var(--fd-amber)] bg-[var(--fd-amber-soft)] p-4 text-[var(--fd-amber-text)]"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <TriangleAlert size={18} className="mt-0.5 shrink-0" aria-hidden />
          <div className="min-w-0">
            <p id="ambiguous-guardian-title" className="text-sm font-semibold">
              لم يتم تأكيد الاستيراد.
            </p>
            <p className="mt-1 text-[12px] leading-6">
              {rowsNeedResolution(ids.length)} تحديد ولي الأمر. حدد ولي الأمر لكل سطر متأثر
              ثم أعد التأكيد.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="fd-btn fd-btn-secondary h-11 shrink-0 bg-[var(--fd-surface)] px-3 text-[12px]"
        >
          إخفاء
        </button>
      </div>

      {rows.length > 0 && (
        <ul className="mt-3 space-y-2">
          {rows.slice(0, 6).map((row) => (
            <li
              key={row.row_id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] bg-[var(--fd-surface)] px-3 py-2"
            >
              <div className="min-w-0">
                <p className="truncate text-[13px] font-medium text-[var(--fd-ink)]">
                  <bdi dir="auto">{row.guardian_name || "سطر بدون اسم"}</bdi>
                </p>
                <p className="mt-0.5 text-[11px] text-[var(--fd-ink-muted)]">
                  <bdi dir="ltr" className="font-mono">
                    {row.guardian_phone_masked || "—"}
                  </bdi>
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => onReveal(row.row_id, row.guardian_name)}
                  className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                  title="يفتح السطر إن كان في هذه الصفحة، أو يبحث باسم ولي الأمر"
                >
                  عرض السطر
                </button>
                <button
                  type="button"
                  onClick={() => onResolve(row)}
                  className="fd-btn fd-btn-primary h-11 px-3 text-[12px]"
                >
                  تحديد ولي الأمر
                </button>
              </div>
            </li>
          ))}
          {rows.length > 6 && (
            <li className="text-[11px] text-[var(--fd-ink-muted)]">
              و {formatNumber(rows.length - 6)} سطور أخرى.
            </li>
          )}
        </ul>
      )}

      {rows.length === 0 && (
        <p className="mt-3 text-[11px] text-[var(--fd-ink-muted)]">
          افتح الأسطر المتأثرة من الجدول وحدد ولي الأمر من عمود الإجراءات.
        </p>
      )}
    </section>
  );
}
