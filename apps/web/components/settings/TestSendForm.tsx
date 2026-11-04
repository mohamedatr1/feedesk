"use client";

import { useState } from "react";
import { FlaskConical, Info, Send } from "lucide-react";
import { ApiError, api, formatDateTime } from "@/lib/api";
import type { MessagingProviderStatus, MessagingTestSendResult } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";
import {
  isDryRunMode,
  isE164,
  outcomeLabel,
  outcomeTone,
  testModeLabel,
} from "./provider-format";

type FieldErrors = { recipient?: string; message?: string };

function ResultRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
      <dt className="text-[11px] text-[var(--fd-ink-subtle)]">{label}</dt>
      <dd className="min-w-0 text-[12px] font-medium text-[var(--fd-ink)]">{children}</dd>
    </div>
  );
}

export function TestSendForm({
  status,
  locale,
  timeZone,
}: {
  status: MessagingProviderStatus;
  locale?: string | null;
  timeZone?: string | null;
}) {
  const [recipient, setRecipient] = useState("");
  const [message, setMessage] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [requestError, setRequestError] = useState<string | null>(null);
  const [result, setResult] = useState<MessagingTestSendResult | null>(null);
  const [busy, setBusy] = useState(false);

  const dryRun = isDryRunMode(status.test_send_mode);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;

    const trimmedRecipient = recipient.trim();
    const trimmedMessage = message.trim();
    const errors: FieldErrors = {};
    if (!trimmedRecipient) {
      errors.recipient = "أدخل رقم المستلم.";
    } else if (!isE164(trimmedRecipient)) {
      errors.recipient = "استخدم صيغة E.164، مثل +9639XXXXXXXX.";
    }
    if (!trimmedMessage) errors.message = "أدخل نص الرسالة.";
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setRequestError(null);
      return;
    }

    setBusy(true);
    setFieldErrors({});
    setRequestError(null);
    setResult(null);
    try {
      const data = await api.testSendMessage({
        recipient: trimmedRecipient,
        message: trimmedMessage,
      });
      setResult(data);
    } catch (err) {
      setRequestError(
        err instanceof ApiError ? err.messageAr : "تعذر تنفيذ الإرسال التجريبي.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="fd-card fd-card-pad" aria-labelledby="provider-test-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <Send size={16} className="mt-0.5 shrink-0 text-[var(--fd-brand)]" aria-hidden />
          <div className="min-w-0">
            <h3 id="provider-test-title" className="text-sm font-semibold text-[var(--fd-ink)]">
              إرسال اختبار
            </h3>
            <p className="mt-0.5 text-[11px] leading-5 text-[var(--fd-ink-muted)]">
              رسالة واحدة للتحقق من الاتصال. لا تُدرج في أي حملة أو قائمة إرسال.
            </p>
          </div>
        </div>
        <span className="fd-pill fd-pill-amber">
          <FlaskConical size={12} aria-hidden />
          {dryRun ? "محاكاة (dry-run)" : testModeLabel(status.test_send_mode)}
        </span>
      </div>

      <p className="mt-4 flex items-start gap-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] px-3 py-2 text-[11px] leading-5 text-[var(--fd-ink-muted)]">
        <Info size={14} className="mt-0.5 shrink-0" aria-hidden />
        <span>
          يُقبل الإرسال فقط عبر قائمة السماح أو المزوّد الوهمي، ولا يخرج أي رسالة حقيقية إلى أولياء
          الأمور في هذه المرحلة.
        </span>
      </p>

      <form onSubmit={onSubmit} className="mt-4 space-y-4" noValidate>
        <div>
          <label htmlFor="test_recipient" className="fd-label">
            رقم المستلم
          </label>
          <input
            id="test_recipient"
            type="tel"
            inputMode="tel"
            className="fd-input h-11 text-left"
            dir="ltr"
            value={recipient}
            onChange={(event) => {
              setRecipient(event.target.value);
              if (fieldErrors.recipient) {
                setFieldErrors((prev) => ({ ...prev, recipient: undefined }));
              }
            }}
            placeholder="+9639XXXXXXXX"
            autoComplete="off"
            spellCheck={false}
            disabled={busy}
            aria-invalid={fieldErrors.recipient ? true : undefined}
            aria-describedby={
              fieldErrors.recipient ? "test_recipient_error" : "test_recipient_hint"
            }
            required
          />
          {fieldErrors.recipient ? (
            <p id="test_recipient_error" className="mt-1 text-[11px] text-[var(--fd-red-text)]">
              {fieldErrors.recipient}
            </p>
          ) : (
            <p id="test_recipient_hint" className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">
              صيغة دولية تبدأ بـ + ثم رمز الدولة.
            </p>
          )}
        </div>

        <div>
          <label htmlFor="test_message" className="fd-label">
            نص الرسالة
          </label>
          <textarea
            id="test_message"
            className="fd-input h-auto min-h-[88px] py-2 leading-6"
            dir="auto"
            rows={3}
            value={message}
            onChange={(event) => {
              setMessage(event.target.value);
              if (fieldErrors.message) {
                setFieldErrors((prev) => ({ ...prev, message: undefined }));
              }
            }}
            placeholder="رسالة اختبار من FeeDesk."
            disabled={busy}
            aria-invalid={fieldErrors.message ? true : undefined}
            aria-describedby={fieldErrors.message ? "test_message_error" : undefined}
            required
          />
          {fieldErrors.message && (
            <p id="test_message_error" className="mt-1 text-[11px] text-[var(--fd-red-text)]">
              {fieldErrors.message}
            </p>
          )}
        </div>

        {requestError && (
          <p
            role="alert"
            className="rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] leading-5 text-[var(--fd-red-text)]"
          >
            {requestError}
          </p>
        )}

        <button type="submit" className="fd-btn fd-btn-primary h-11 w-full" disabled={busy}>
          <Send size={15} aria-hidden />
          {busy ? "جارٍ الإرسال التجريبي..." : "إرسال تجريبي"}
        </button>
      </form>

      {result && (
        <div
          role="status"
          aria-live="polite"
          className="mt-4 rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] bg-[var(--fd-surface-alt)] px-3 py-3"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <StatusPill tone={outcomeTone(result.outcome)}>
              {outcomeLabel(result.outcome)}
            </StatusPill>
            {result.dry_run && (
              <span className="fd-pill fd-pill-amber">
                <FlaskConical size={12} aria-hidden />
                محاكاة — لم تُرسل رسالة فعلية
              </span>
            )}
          </div>

          <dl className="mt-3 space-y-1.5">
            <ResultRow label="المستلم">
              {result.recipient_masked ? (
                <bdi dir="ltr">{result.recipient_masked}</bdi>
              ) : (
                "—"
              )}
            </ResultRow>
            <ResultRow label="حالة المزوّد">
              {result.provider_status ? <bdi dir="auto">{result.provider_status}</bdi> : "—"}
            </ResultRow>
            <ResultRow label="معرّف الرسالة">
              {result.provider_message_id ? (
                <bdi dir="ltr" className="break-all font-mono text-[11px]">
                  {result.provider_message_id}
                </bdi>
              ) : (
                "—"
              )}
            </ResultRow>
            <ResultRow label="الوقت">
              {result.sent_at ? (
                <bdi dir="ltr">{formatDateTime(result.sent_at, { locale, timeZone })}</bdi>
              ) : (
                "—"
              )}
            </ResultRow>
          </dl>

          {(result.error_code || result.error_summary) && (
            <div className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[11px] leading-5 text-[var(--fd-red-text)]">
              {result.error_code && (
                <p className="font-mono" dir="ltr">
                  {result.error_code}
                </p>
              )}
              {result.error_summary && (
                <p className="mt-0.5" dir="auto">
                  {result.error_summary}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
