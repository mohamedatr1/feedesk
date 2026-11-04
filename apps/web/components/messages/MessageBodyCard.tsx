"use client";

import { Copy } from "lucide-react";
import { useCopyFeedback } from "@/components/messages/copy";

export function MessageBodyCard({ body }: { body: string | null }) {
  const { status, copy } = useCopyFeedback();
  const hasBody = Boolean(body && body.trim());

  return (
    <section className="fd-card fd-card-pad" aria-labelledby="message-body-title">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="h-4 w-1 rounded-full bg-[var(--fd-brand)]" aria-hidden />
          <h2 id="message-body-title" className="text-[15px] font-bold text-[var(--fd-ink)]">
            نص الرسالة
          </h2>
        </div>
        <button
          type="button"
          className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
          onClick={() => {
            if (hasBody && body) void copy(body, "تم نسخ نص الرسالة.");
          }}
          disabled={!hasBody}
        >
          <Copy size={15} aria-hidden />
          نسخ النص
        </button>
      </div>

      {hasBody ? (
        <div
          dir="rtl"
          lang="ar"
          className="mt-3 min-h-[96px] max-w-[68ch] whitespace-pre-wrap rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] p-4 text-[15px] leading-[1.9] text-[var(--fd-ink)]"
          style={{ overflowWrap: "anywhere", userSelect: "text" }}
        >
          {body}
        </div>
      ) : (
        <p className="mt-3 text-[13px] text-[var(--fd-ink-subtle)]">
          لا يوجد نص محفوظ لهذه الرسالة.
        </p>
      )}

      <p className="mt-2 text-[12px] text-[var(--fd-ink-subtle)]">
        نسخة مثبّتة وقت الاعتماد. لا تتغيّر إذا عُدّل القالب لاحقًا.
      </p>

      <p role="status" className="mt-1 min-h-[18px] text-[12px] text-[var(--fd-ink-muted)]">
        {status}
      </p>
    </section>
  );
}
