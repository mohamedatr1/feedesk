import { AlertCircle, TriangleAlert } from "lucide-react";
import type { ImportIssue } from "@/lib/api";

export function IssueList({
  issues,
  emptyLabel,
  className = "",
  showCodes = false,
  muted = false,
}: {
  issues: ImportIssue[];
  emptyLabel?: string;
  className?: string;
  showCodes?: boolean;
  muted?: boolean;
}) {
  if (issues.length === 0) {
    return emptyLabel ? (
      <p className={`text-[12px] text-[var(--fd-ink-subtle)] ${className}`}>{emptyLabel}</p>
    ) : null;
  }

  return (
    <ul className={`space-y-1.5 ${className}`}>
      {issues.map((issue, index) => {
        const isError = issue.severity === "error";
        const Icon = isError ? AlertCircle : TriangleAlert;
        return (
          <li
            key={`${issue.code}-${index}`}
            className={`flex items-start gap-2 rounded-[var(--fd-radius-control)] px-2.5 py-2 text-[12px] leading-5 ${
              muted
                ? "bg-[var(--fd-surface-alt)] text-[var(--fd-ink-muted)]"
                : isError
                  ? "bg-[var(--fd-red-soft)] text-[var(--fd-red-text)]"
                  : "bg-[var(--fd-amber-soft)] text-[var(--fd-amber-text)]"
            }`}
          >
            <Icon size={14} className="mt-0.5 shrink-0" aria-hidden />
            <span>
              {issue.message_ar}
              {showCodes && (
                <bdi
                  dir="ltr"
                  className="ms-1 font-mono text-[10px] text-[var(--fd-ink-subtle)]"
                >
                  {issue.code}
                </bdi>
              )}
              <span className="sr-only">
                {muted
                  ? " (سجل مستبعد — لا يمنع التأكيد)"
                  : isError
                    ? " (خطأ مانع للتأكيد)"
                    : " (تحذير)"}
              </span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
