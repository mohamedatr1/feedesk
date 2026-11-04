"use client";

import { useEffect, useRef, useState } from "react";
import { Copy } from "lucide-react";

function fallbackCopy(value: string): boolean {
  try {
    const area = document.createElement("textarea");
    area.value = value;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(area);
    return ok;
  } catch {
    return false;
  }
}

export function SnapshotHash({
  hash,
  compact = false,
}: {
  hash: string;
  compact?: boolean;
}) {
  const [status, setStatus] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  async function copy() {
    let ok = false;
    try {
      await navigator.clipboard.writeText(hash);
      ok = true;
    } catch {
      ok = fallbackCopy(hash);
    }
    setStatus(ok ? "تم نسخ البصمة." : "تعذر النسخ. حدّد النص وانسخه يدويًا.");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setStatus(null), 4000);
  }

  return (
    <div className={compact ? "" : "mt-2"}>
      {!compact && (
        <>
          <p className="text-[12px] font-medium text-[var(--fd-ink-muted)]">بصمة النسخة</p>
          <p className="mt-0.5 text-[11px] leading-5 text-[var(--fd-ink-subtle)]">
            تثبت أن هذه النسخة لم تتغيّر. تُحسب من بيانات الحملة والمستلمين عند الاعتماد.
          </p>
        </>
      )}
      <div className="mt-2 flex flex-wrap items-start gap-2">
        <code
          className="min-w-0 flex-1 select-all break-all rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] p-3 font-mono text-[11px] text-[var(--fd-ink-muted)]"
          dir="ltr"
          lang="en"
        >
          {hash}
        </code>
        <button
          type="button"
          onClick={copy}
          className="fd-btn fd-btn-secondary h-11 shrink-0 px-3 text-[12px]"
          aria-label="نسخ بصمة النسخة"
        >
          <Copy size={15} aria-hidden />
          نسخ
        </button>
      </div>
      <p role="status" className="mt-1 min-h-[18px] text-[11px] text-[var(--fd-ink-muted)]">
        {status}
      </p>
    </div>
  );
}
