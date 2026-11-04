"use client";

import { useState } from "react";
import { Eye, EyeOff, ShieldCheck } from "lucide-react";
import { ApiError, api, type MessagingChannel } from "@/lib/api";
import type { MessagingProviderStatus } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";
import { MESSAGING_CHANNELS, isMessagingChannel } from "./provider-format";

type FieldErrors = { api_key?: string; sender_id?: string };

export function RotateCredentialForm({
  status,
  onRotated,
}: {
  status: MessagingProviderStatus;
  onRotated: (next: MessagingProviderStatus) => void | Promise<void>;
}) {
  const [apiKey, setApiKey] = useState("");
  // Sender ID and channel are not secret, so they start from the saved state.
  const [senderId, setSenderId] = useState(status.sender_id ?? "");
  const [channel, setChannel] = useState<MessagingChannel>(
    isMessagingChannel(status.channel) ? status.channel : "local_sms",
  );
  const [revealKey, setRevealKey] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;

    const errors: FieldErrors = {};
    if (!apiKey.trim()) errors.api_key = "أدخل مفتاح API قبل الحفظ.";
    if (!senderId.trim()) errors.sender_id = "أدخل معرّف المرسل.";
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setNotice(null);
      return;
    }

    setBusy(true);
    setFieldErrors({});
    setNotice(null);
    try {
      const next = await api.updateMessagingCredential({
        api_key: apiKey.trim(),
        sender_id: senderId.trim(),
        channel,
      });
      setNotice({
        kind: "success",
        text: "تم حفظ بيانات الاعتماد وتشفير المفتاح على الخادم. المفتاح لن يُعرض مرة أخرى.",
      });
      await onRotated(next);
    } catch (err) {
      const base =
        err instanceof ApiError ? err.messageAr : "تعذر حفظ بيانات الاعتماد.";
      setNotice({
        kind: "error",
        text: `${base} أعد إدخال المفتاح للمحاولة مرة أخرى.`,
      });
    } finally {
      // Write-only field: whether the request succeeded or failed, the typed
      // key is dropped from component state as soon as the request is done.
      setApiKey("");
      setRevealKey(false);
      setBusy(false);
    }
  }

  return (
    <section className="fd-card fd-card-pad" aria-labelledby="provider-credential-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <ShieldCheck
            size={17}
            className="mt-0.5 shrink-0 text-[var(--fd-brand)]"
            aria-hidden
          />
          <div className="min-w-0">
            <h3
              id="provider-credential-title"
              className="text-sm font-semibold text-[var(--fd-ink)]"
            >
              تدوير بيانات الاعتماد
            </h3>
            <p className="mt-0.5 text-[11px] leading-5 text-[var(--fd-ink-muted)]">
              يحل المفتاح الجديد محل القديم فورًا.
            </p>
          </div>
        </div>
        <StatusPill tone={status.configured ? "green" : "neutral"}>
          {status.configured
            ? status.key_version != null
              ? `الإصدار ${status.key_version}`
              : "مهيّأ"
            : "لا يوجد مفتاح"}
        </StatusPill>
      </div>

      <p className="mt-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] px-3 py-2 text-[11px] leading-5 text-[var(--fd-ink-muted)]">
        يُشفَّر المفتاح على الخادم ولا يُعاد إلى المتصفح بعد الحفظ. لا يُملأ الحقل مسبقًا، ولن
        يظهر المفتاح في هذه الصفحة مرة أخرى.
      </p>

      <form onSubmit={onSubmit} className="mt-4 space-y-4" noValidate>
        <div>
          <label htmlFor="provider_api_key" className="fd-label">
            مفتاح API
          </label>
          <div className="relative">
            <input
              id="provider_api_key"
              name="messaging_api_key"
              type={revealKey ? "text" : "password"}
              className="fd-input h-11 pe-14 text-left font-mono text-[12px]"
              dir="ltr"
              value={apiKey}
              onChange={(event) => {
                setApiKey(event.target.value);
                if (fieldErrors.api_key) setFieldErrors((prev) => ({ ...prev, api_key: undefined }));
              }}
              placeholder="••••••••••••"
              autoComplete="off"
              spellCheck={false}
              disabled={busy}
              aria-invalid={fieldErrors.api_key ? true : undefined}
              aria-describedby={
                fieldErrors.api_key ? "provider_api_key_error" : "provider_api_key_hint"
              }
              required
            />
            <button
              type="button"
              onClick={() => setRevealKey((value) => !value)}
              className="fd-btn fd-btn-ghost absolute inset-y-0 start-1 my-auto h-11 w-11 shrink-0 px-0"
              aria-label={revealKey ? "إخفاء المفتاح" : "إظهار المفتاح"}
              aria-pressed={revealKey}
              disabled={busy}
            >
              {revealKey ? <EyeOff size={15} aria-hidden /> : <Eye size={15} aria-hidden />}
            </button>
          </div>
          {fieldErrors.api_key ? (
            <p id="provider_api_key_error" className="mt-1 text-[11px] text-[var(--fd-red-text)]">
              {fieldErrors.api_key}
            </p>
          ) : (
            <p id="provider_api_key_hint" className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">
              يُرسل مرة واحدة عند الحفظ فقط.
            </p>
          )}
        </div>

        <div>
          <label htmlFor="provider_sender_id" className="fd-label">
            معرّف المرسل
          </label>
          <input
            id="provider_sender_id"
            className="fd-input h-11 text-left"
            dir="ltr"
            value={senderId}
            onChange={(event) => {
              setSenderId(event.target.value);
              if (fieldErrors.sender_id) {
                setFieldErrors((prev) => ({ ...prev, sender_id: undefined }));
              }
            }}
            placeholder="SCHOOL"
            maxLength={64}
            autoComplete="off"
            disabled={busy}
            aria-invalid={fieldErrors.sender_id ? true : undefined}
            aria-describedby={fieldErrors.sender_id ? "provider_sender_id_error" : undefined}
            required
          />
          {fieldErrors.sender_id && (
            <p
              id="provider_sender_id_error"
              className="mt-1 text-[11px] text-[var(--fd-red-text)]"
            >
              {fieldErrors.sender_id}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="provider_channel" className="fd-label">
            القناة
          </label>
          <select
            id="provider_channel"
            className="fd-input h-11"
            value={channel}
            onChange={(event) => setChannel(event.target.value as MessagingChannel)}
            disabled={busy}
          >
            {MESSAGING_CHANNELS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>

        {notice && (
          <p
            role={notice.kind === "error" ? "alert" : "status"}
            className={`rounded-[var(--fd-radius-control)] px-3 py-2 text-[12px] leading-5 ${
              notice.kind === "success"
                ? "bg-[var(--fd-green-soft)] text-[var(--fd-green-text)]"
                : "bg-[var(--fd-red-soft)] text-[var(--fd-red-text)]"
            }`}
          >
            {notice.text}
          </p>
        )}

        <button type="submit" className="fd-btn fd-btn-primary h-11 w-full" disabled={busy}>
          {busy ? "جارٍ حفظ المفتاح..." : "حفظ بيانات الاعتماد"}
        </button>
      </form>
    </section>
  );
}
