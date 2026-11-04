import type { ReactNode } from "react";

const TOKEN = /(\{\{\s*[A-Za-z0-9_]+\s*\}\})/g;

/**
 * Raw template text, never interpolated. Variables render as chips; everything
 * else is literal so the author sees exactly what the API stores.
 */
export function TemplateBody({
  body,
  className = "",
  ariaLabel = "نص القالب",
}: {
  body: string;
  className?: string;
  ariaLabel?: string;
}) {
  if (!body) {
    return (
      <p className="rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] p-4 text-[13px] text-[var(--fd-ink-subtle)]">
        لا يوجد نص.
      </p>
    );
  }

  const parts = body.split(TOKEN);
  const nodes: ReactNode[] = parts.map((part, index) => {
    if (/^\{\{/.test(part)) {
      const name = part.replace(/[{}]/g, "").trim();
      return (
        <span
          key={`var-${index}`}
          className="mx-0.5 inline-flex items-center rounded-[6px] border border-[var(--fd-line-strong)] bg-[var(--fd-surface)] px-1.5 py-0.5 font-mono text-[12px] text-[var(--fd-brand)]"
          dir="ltr"
          lang="en"
        >
          {`{{${name}}}`}
        </span>
      );
    }
    return <span key={`text-${index}`}>{part}</span>;
  });

  return (
    <div
      className={`whitespace-pre-wrap break-words rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] p-4 text-[14px] leading-[1.9] text-[var(--fd-ink)] ${className}`}
      dir="rtl"
      role="region"
      aria-label={ariaLabel}
      tabIndex={0}
    >
      {nodes}
    </div>
  );
}
