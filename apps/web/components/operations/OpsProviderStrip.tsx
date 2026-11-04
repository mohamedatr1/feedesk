import Link from "next/link";
import { ServerCog, TriangleAlert } from "lucide-react";
import { formatNumber, type MessagingOpsProvider } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";
import { credentialSourceLabel } from "@/components/settings/provider-format";

/**
 * One line of provider truth: name, readiness, where the credential came from
 * and its version. The credential itself has no code path into this UI.
 */
export function OpsProviderStrip({ provider }: { provider: MessagingOpsProvider }) {
  return (
    <section className="fd-card mb-5 overflow-hidden" aria-labelledby="ops-provider-title">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--fd-line)] px-5 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--fd-surface-alt)] text-[var(--fd-ink-muted)]">
            <ServerCog size={19} strokeWidth={1.8} aria-hidden />
          </span>
          <div className="min-w-0">
            <h2 id="ops-provider-title" className="text-[13px] font-semibold text-[var(--fd-ink)]">
              مزوّد الرسائل
            </h2>
            <p className="truncate text-[12px] text-[var(--fd-ink-muted)]">
              <bdi dir="auto">{provider.name || "—"}</bdi>
            </p>
          </div>
        </div>
        <StatusPill tone={provider.configured ? "green" : "amber"}>
          {provider.configured ? "مهيّأ" : "غير مهيّأ"}
        </StatusPill>
      </div>

      <dl className="grid grid-cols-1 gap-px bg-[var(--fd-line)] sm:grid-cols-2">
        <div className="bg-[var(--fd-surface)] px-5 py-3">
          <dt className="text-[11px] text-[var(--fd-ink-subtle)]">مصدر بيانات الاعتماد</dt>
          <dd className="mt-0.5 text-[13px] text-[var(--fd-ink)]">
            {credentialSourceLabel(provider.credential_source)}
          </dd>
        </div>
        <div className="bg-[var(--fd-surface)] px-5 py-3">
          <dt className="text-[11px] text-[var(--fd-ink-subtle)]">إصدار المفتاح</dt>
          <dd className="mt-0.5 text-[13px] text-[var(--fd-ink)]">
            {provider.key_version === null ? (
              "—"
            ) : (
              <bdi dir="ltr" className="tabular-nums">
                v{formatNumber(provider.key_version)}
              </bdi>
            )}
            <span className="ms-2 text-[11px] text-[var(--fd-ink-subtle)]">
              المفتاح نفسه لا يظهر في هذه الشاشة.
            </span>
          </dd>
        </div>
      </dl>

      {provider.credential_error && (
        <div className="flex items-start gap-2 border-t border-[var(--fd-line)] bg-[var(--fd-red-soft)] px-5 py-3 text-[12px] leading-6 text-[var(--fd-red-text)]">
          <TriangleAlert size={15} className="mt-0.5 shrink-0" aria-hidden />
          <p className="min-w-0 break-words">
            <span className="font-semibold">تعذر تحميل بيانات الاعتماد. </span>
            {provider.credential_error}
          </p>
        </div>
      )}

      {!provider.configured && !provider.credential_error && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--fd-line)] bg-[var(--fd-amber-soft)] px-5 py-3 text-[12px] text-[var(--fd-amber-text)]">
          <p className="flex min-w-0 items-start gap-2">
            <TriangleAlert size={15} className="mt-0.5 shrink-0" aria-hidden />
            <span>لم تُضبط بيانات اعتماد المزوّد بعد، لذا لا تُرسل رسائل.</span>
          </p>
          <Link
            href="/settings"
            className="fd-btn fd-btn-secondary h-11 shrink-0 bg-[var(--fd-surface)] px-3 text-[12px]"
          >
            بيانات الاعتماد في الإعدادات
          </Link>
        </div>
      )}
    </section>
  );
}
