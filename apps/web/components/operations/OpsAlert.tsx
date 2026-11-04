"use client";

import { RefreshCw } from "lucide-react";

/**
 * The single inline error banner for the console. Retry is optional so a
 * section that cannot be retried on its own (provider strip) stays calm.
 */
export function OpsAlert({
  children,
  onRetry,
  className = "",
}: {
  children: React.ReactNode;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={`flex flex-wrap items-center justify-between gap-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-4 py-3 text-[12px] text-[var(--fd-red-text)] ${className}`}
    >
      <span className="min-w-0">{children}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="fd-btn fd-btn-secondary h-11 shrink-0 px-3 text-[12px]"
        >
          <RefreshCw size={14} aria-hidden />
          إعادة المحاولة
        </button>
      )}
    </div>
  );
}
