import type { ReactNode } from "react";

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-col gap-3 sm:mb-6 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between sm:gap-4">
      <div className="min-w-0">
        <h1 className="break-words text-2xl font-bold leading-tight text-[var(--fd-ink)] sm:text-[30px]">
          {title}
        </h1>
        {subtitle && <p className="mt-1 break-words text-sm text-[var(--fd-ink-muted)]">{subtitle}</p>}
      </div>
      {action && <div className="w-full shrink-0 sm:w-auto [&>*]:max-w-full">{action}</div>}
    </div>
  );
}
