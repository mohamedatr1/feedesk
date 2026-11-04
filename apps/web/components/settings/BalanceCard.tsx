"use client";

import { RefreshCw, Wallet } from "lucide-react";
import type { MessagingBalance } from "@/lib/api";
import { formatBalanceValue, preflightLabel } from "./provider-format";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
      <dt className="text-[11px] text-[var(--fd-ink-subtle)]">{label}</dt>
      <dd className="min-w-0 text-[12px] font-medium text-[var(--fd-ink)]">{children}</dd>
    </div>
  );
}

export function BalanceCard({
  balance,
  error,
  busy,
  onRefresh,
}: {
  balance: MessagingBalance | null;
  error: string | null;
  busy: boolean;
  onRefresh: () => void;
}) {
  return (
    <section
      className="fd-card fd-card-pad"
      aria-labelledby="provider-balance-title"
      aria-busy={busy}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <Wallet size={16} className="mt-0.5 shrink-0 text-[var(--fd-brand)]" aria-hidden />
          <div className="min-w-0">
            <h3 id="provider-balance-title" className="text-sm font-semibold text-[var(--fd-ink)]">
              رصيد المزوّد
            </h3>
            <p className="mt-0.5 text-[11px] leading-5 text-[var(--fd-ink-muted)]">
              فحص مسبق قبل أي إرسال.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={busy}
          className="fd-btn fd-btn-ghost h-11 w-11 shrink-0 px-0"
          aria-label="تحديث الرصيد"
          title="تحديث الرصيد"
        >
          <RefreshCw size={16} className={busy ? "animate-spin" : undefined} aria-hidden />
        </button>
      </div>

      {busy && !balance ? (
        <div className="mt-4 space-y-2">
          <div className="fd-skeleton h-8 w-32" />
          <div className="fd-skeleton h-4 w-full" />
        </div>
      ) : error && !balance ? (
        <p
          role="alert"
          className="mt-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] leading-5 text-[var(--fd-red-text)]"
        >
          {error}
        </p>
      ) : balance ? (
        <>
          {balance.available ? (
            <>
              <div className="mt-4">
                <p className="text-[11px] text-[var(--fd-ink-subtle)]">الرصيد المتاح</p>
                <p className="mt-1 flex flex-wrap items-baseline gap-2">
                  <span className="text-[28px] font-bold leading-none tracking-tight text-[var(--fd-ink)] tabular-nums">
                    {formatBalanceValue(balance.balance)}
                  </span>
                  {balance.currency && (
                    <span className="text-[12px] font-semibold text-[var(--fd-ink-muted)]">
                      <bdi dir="ltr">{balance.currency}</bdi>
                    </span>
                  )}
                </p>
              </div>
              <dl className="mt-3 space-y-1.5 border-t border-[var(--fd-line)] pt-3">
                <Row label="المزوّد">
                  <bdi dir="ltr">{balance.provider || "—"}</bdi>
                </Row>
                <Row label="الفحص المسبق">{preflightLabel(balance.preflight)}</Row>
              </dl>
            </>
          ) : (
            <div className="mt-4 overflow-hidden rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] px-3 py-2.5 text-[var(--fd-amber-text)]">
              <p className="text-[12px] font-semibold">الرصيد غير متاح</p>
              <p className="mt-0.5 text-[11px] leading-5">
                <span className="font-medium">السبب: </span>
                <bdi dir="auto">
                  {balance.reason?.trim() || "لا يوجد سبب محدد من الخادم."}
                </bdi>
              </p>
              {balance.provider && (
                <p className="mt-1 text-[11px] text-[var(--fd-amber-text)]">
                  المزوّد: <bdi dir="ltr">{balance.provider}</bdi>
                </p>
              )}
              <p className="mt-1 text-[11px] text-[var(--fd-amber-text)]">
                الفحص المسبق: {preflightLabel(balance.preflight)}
              </p>
            </div>
          )}

          {error && (
            <p
              role="alert"
              className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[11px] leading-5 text-[var(--fd-red-text)]"
            >
              {error}
            </p>
          )}
        </>
      ) : (
        <p className="mt-4 text-[12px] text-[var(--fd-ink-muted)]">لم يُحمَّل الرصيد بعد.</p>
      )}
    </section>
  );
}
