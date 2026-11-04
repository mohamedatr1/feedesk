"use client";

import { useEffect, useRef, useState } from "react";
import { FlaskConical, MessageSquare } from "lucide-react";
import {
  ApiError,
  api,
  type MessagingBalance,
  type MessagingProviderStatus,
} from "@/lib/api";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ProviderStatusCard } from "./ProviderStatusCard";
import { RotateCredentialForm } from "./RotateCredentialForm";
import { TestSendForm } from "./TestSendForm";
import { BalanceCard } from "./BalanceCard";
import { isDryRunMode, testModeLabel } from "./provider-format";

function apiMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.messageAr : fallback;
}

/**
 * Admin-only messaging provider controls.
 *
 * The panel is mounted only for admins; it never requests permissions on its
 * own and the API key never lives anywhere except the write-only form field.
 */
export function MessagingProviderPanel({
  locale,
  timeZone,
}: {
  locale?: string | null;
  timeZone?: string | null;
}) {
  const mountedRef = useRef(true);
  const [status, setStatus] = useState<MessagingProviderStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [balance, setBalance] = useState<MessagingBalance | null>(null);
  const [balanceError, setBalanceError] = useState<string | null>(null);
  const [balanceBusy, setBalanceBusy] = useState(false);
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [revokeOpen, setRevokeOpen] = useState(false);
  const [revokeBusy, setRevokeBusy] = useState(false);
  const [revokeError, setRevokeError] = useState<string | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    void loadStatus();
    void loadBalance();
    return () => {
      mountedRef.current = false;
    };
    // Load once on mount; both loaders are idempotent.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadStatus() {
    setStatusLoading(true);
    setStatusError(null);
    try {
      const data = await api.getMessagingProvider();
      if (mountedRef.current) setStatus(data);
    } catch (err) {
      if (mountedRef.current) {
        setStatusError(apiMessage(err, "تعذر تحميل حالة مزوّد الرسائل."));
      }
    } finally {
      if (mountedRef.current) setStatusLoading(false);
    }
  }

  async function loadBalance() {
    setBalanceBusy(true);
    try {
      const data = await api.getMessagingBalance();
      if (!mountedRef.current) return;
      setBalance(data);
      setBalanceError(null);
    } catch (err) {
      if (mountedRef.current) {
        setBalanceError(apiMessage(err, "تعذر تحميل رصيد المزوّد."));
      }
    } finally {
      if (mountedRef.current) setBalanceBusy(false);
    }
  }

  async function handleRotated(next: MessagingProviderStatus) {
    if (!mountedRef.current) return;
    setStatus(next);
    setStatusError(null);
    setNotice(null);
    // The saved credential changed, so any balance shown before is stale.
    setBalance(null);
    setBalanceError(null);
    await loadBalance();
  }

  function openRevoke() {
    setRevokeError(null);
    setRevokeBusy(false);
    setRevokeOpen(true);
  }

  async function confirmRevoke() {
    setRevokeBusy(true);
    setRevokeError(null);
    try {
      const next = await api.revokeMessagingCredential();
      if (!mountedRef.current) return;
      setStatus(next);
      setStatusError(null);
      setRevokeOpen(false);
      setNotice({
        kind: "success",
        text: "تم إبطال بيانات الاعتماد. الإرسال والتحقق من الرصيد معطّلان حتى حفظ مفتاح جديد.",
      });
      setBalance(null);
      setBalanceError(null);
      void loadBalance();
    } catch (err) {
      if (mountedRef.current) {
        setRevokeError(apiMessage(err, "تعذر إبطال بيانات الاعتماد."));
      }
    } finally {
      if (mountedRef.current) setRevokeBusy(false);
    }
  }

  const dryRun = status ? isDryRunMode(status.test_send_mode) : false;

  return (
    <section className="mt-8" aria-labelledby="messaging-provider-title">
      <div className="border-t border-[var(--fd-line)] pt-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <span
              className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--fd-brand-soft)] text-[var(--fd-brand)]"
              aria-hidden
            >
              <MessageSquare size={17} />
            </span>
            <div className="min-w-0">
              <h2
                id="messaging-provider-title"
                className="text-[18px] font-bold leading-tight text-[var(--fd-ink)]"
              >
                مزوّد الرسائل
              </h2>
              <p className="mt-1 max-w-[65ch] text-[12px] leading-5 text-[var(--fd-ink-muted)]">
                الاتصال بمزوّد الرسائل وتدوير المفتاح وإرسال اختبار ومتابعة الرصيد. هذه
                الإعدادات لمدير النظام فقط.
              </p>
            </div>
          </div>

          {status && dryRun && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="fd-pill fd-pill-amber">
                <FlaskConical size={12} aria-hidden />
                {testModeLabel(status.test_send_mode)}
              </span>
            </div>
          )}
        </div>
      </div>

      {notice && (
        <p
          role={notice.kind === "error" ? "alert" : "status"}
          className={`mt-4 rounded-[var(--fd-radius-control)] px-3 py-2 text-[12px] leading-5 ${
            notice.kind === "success"
              ? "bg-[var(--fd-green-soft)] text-[var(--fd-green-text)]"
              : "bg-[var(--fd-red-soft)] text-[var(--fd-red-text)]"
          }`}
        >
          {notice.text}
        </p>
      )}

      {statusLoading && !status ? (
        <div className="mt-4 space-y-5">
          <div className="fd-card fd-card-pad space-y-4">
            <div className="fd-skeleton h-6 w-40" />
            <div className="fd-skeleton h-24 w-full" />
          </div>
          <div className="grid items-start gap-5 xl:grid-cols-2">
            <div className="fd-card fd-card-pad space-y-4">
              <div className="fd-skeleton h-6 w-36" />
              <div className="fd-skeleton h-10 w-full" />
              <div className="fd-skeleton h-10 w-full" />
              <div className="fd-skeleton h-10 w-full" />
            </div>
            <div className="fd-card fd-card-pad space-y-4">
              <div className="fd-skeleton h-6 w-28" />
              <div className="fd-skeleton h-10 w-full" />
              <div className="fd-skeleton h-10 w-full" />
            </div>
          </div>
        </div>
      ) : statusError && !status ? (
        <div className="fd-card fd-card-pad mt-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[var(--fd-red-text)]">
                تعذر تحميل حالة مزوّد الرسائل
              </p>
              <p
                role="alert"
                className="mt-1 text-[12px] leading-5 text-[var(--fd-ink-muted)]"
              >
                {statusError}
              </p>
            </div>
            <button
              type="button"
              className="fd-btn fd-btn-secondary h-11"
              onClick={() => void loadStatus()}
            >
              إعادة المحاولة
            </button>
          </div>
        </div>
      ) : status ? (
        <div className="mt-4 space-y-5">
          <ProviderStatusCard
            status={status}
            locale={locale}
            timeZone={timeZone}
            onRevoke={openRevoke}
            revokeBusy={revokeBusy}
          />

          <div className="grid items-start gap-5 xl:grid-cols-2">
            <RotateCredentialForm status={status} onRotated={handleRotated} />
            <div className="space-y-5">
              <TestSendForm status={status} locale={locale} timeZone={timeZone} />
              <BalanceCard
                balance={balance}
                error={balanceError}
                busy={balanceBusy}
                onRefresh={() => void loadBalance()}
              />
            </div>
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={revokeOpen}
        title="إبطال بيانات اعتماد المزوّد؟"
        description={
          <>
            سيتوقف الاتصال بمزوّد الرسائل فورًا، ولن يعمل إرسال الاختبار أو التحقق من الرصيد
            حتى تحفظ مفتاحًا جديدًا. لا يمكن التراجع عن هذا الإجراء.
          </>
        }
        confirmLabel="تأكيد الإبطال"
        busyLabel="جارٍ الإبطال..."
        busy={revokeBusy}
        error={revokeError}
        onConfirm={() => void confirmRevoke()}
        onClose={() => {
          if (revokeBusy) return;
          setRevokeOpen(false);
          setRevokeError(null);
        }}
      />
    </section>
  );
}
