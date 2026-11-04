import { AlertCircle, TriangleAlert } from "lucide-react";
import type { ImportIssue } from "@/lib/api";
import { IssueList } from "@/components/imports/IssueList";

/**
 * Row-adjacent issue block. The first issue is always visible; the remainder
 * lives in a native disclosure so nothing important is hover-only.
 */
export function RowIssues({
  id,
  issues,
  className = "",
  isExcluded = false,
}: {
  id?: string;
  issues: ImportIssue[];
  className?: string;
  isExcluded?: boolean;
}) {
  if (issues.length === 0) return null;

  const first = issues.find((issue) => issue.severity === "error") ?? issues[0];
  const rest = issues.filter((issue) => issue !== first);
  const isError = first.severity === "error";
  const Icon = isError ? AlertCircle : TriangleAlert;
  const tone = isExcluded
    ? "text-[var(--fd-ink-muted)]"
    : isError
      ? "text-[var(--fd-red-text)]"
      : "text-[var(--fd-amber-text)]";

  return (
    <div id={id} className={`px-1 py-1.5 ${className}`}>
      <p className={`flex items-start gap-2 text-[12px] leading-5 ${tone}`}>
        <Icon size={15} className="mt-0.5 shrink-0" aria-hidden />
        <span>
          {first.message_ar}
          <span className="sr-only">
            {isExcluded
              ? " (سجل مستبعد — لا يمنع التأكيد)"
              : isError
                ? " (خطأ مانع للتأكيد)"
                : " (تحذير)"}
          </span>
        </span>
      </p>

      {rest.length > 0 && (
        <details className="mt-1 ps-7">
          <summary className="cursor-pointer text-[11px] text-[var(--fd-ink-muted)]">
            عرض كل الملاحظات ({rest.length + 1})
          </summary>
          <IssueList
            issues={rest}
            className="mt-2 max-w-[520px]"
            muted={isExcluded}
          />
        </details>
      )}
    </div>
  );
}
