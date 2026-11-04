"use client";

import { Plus } from "lucide-react";
import type { TemplateVariable } from "@/lib/api";

export function VariablePalette({
  variables,
  error,
  announcement,
  onInsert,
}: {
  variables: TemplateVariable[];
  error: string | null;
  announcement: string | null;
  onInsert: (name: string) => void;
}) {
  if (error) {
    return (
      <p className="rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] p-3 text-[12px] text-[var(--fd-ink-muted)]">
        تعذر تحميل المتغيرات. يمكنك كتابة النص دون إدراج.
      </p>
    );
  }

  return (
    <div>
      <p className="text-[12px] font-medium text-[var(--fd-ink-muted)]">
        المتغيرات المسموحة
      </p>
      <ul className="mt-2 space-y-1.5">
        {variables.map((variable) => (
          <li key={variable.name}>
            <button
              type="button"
              onClick={() => onInsert(variable.name)}
              aria-label={`إدراج متغير ${variable.label}`}
              className="flex min-h-11 w-full flex-wrap items-center justify-between gap-2 rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] px-3 py-2 text-start transition hover:bg-[var(--fd-surface-alt)]"
            >
              <span className="flex items-center gap-1.5">
                <Plus size={14} className="text-[var(--fd-brand)]" aria-hidden />
                <code
                  className="rounded-[6px] bg-[var(--fd-brand-soft)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--fd-brand)]"
                  dir="ltr"
                  lang="en"
                >
                  {`{{${variable.name}}}`}
                </code>
                <span className="text-[12px] text-[var(--fd-ink)]">{variable.label}</span>
              </span>
              <span className="text-[10px] text-[var(--fd-ink-subtle)]">
                {variable.fallback ? `البديل: ${variable.fallback}` : "مطلوب"}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <p role="status" className="mt-1 min-h-[18px] text-[11px] text-[var(--fd-green-text)]">
        {announcement ?? ""}
      </p>
    </div>
  );
}
