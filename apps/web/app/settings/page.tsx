"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BookText, Save, UsersRound } from "lucide-react";
import { ApiError, api, type SchoolSettings } from "@/lib/api";
import { ensureMe, ensureSettings, primeSettings } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { MessagingProviderPanel } from "@/components/settings/MessagingProviderPanel";

export default function SettingsPage() {
  const [form, setForm] = useState<SchoolSettings | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    Promise.all([ensureMe(), ensureSettings()])
      .then(([me, settings]) => {
        setIsAdmin(me.user.role === "admin");
        setForm(settings);
      })
      .catch((err: unknown) => {
        setMessage({
          kind: "error",
          text: err instanceof ApiError ? err.messageAr : "تعذر تحميل الإعدادات.",
        });
      });
  }, []);

  function update<K extends keyof SchoolSettings>(key: K, value: SchoolSettings[K]) {
    setForm((current) => (current ? { ...current, [key]: value } : current));
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form || !isAdmin) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateSettings({
        school_name: form.school_name,
        default_currency: form.default_currency.toUpperCase(),
        currency_symbol: form.currency_symbol,
        timezone: form.timezone,
        locale: form.locale,
        contact_phone: form.contact_phone,
        contact_email: form.contact_email,
        send_limit: Number(form.send_limit),
        batch_limit: Number(form.batch_limit),
      });
      setForm(updated);
      primeSettings(updated);
      setMessage({ kind: "success", text: "تم حفظ الإعدادات." });
    } catch (err) {
      setMessage({
        kind: "error",
        text: err instanceof ApiError ? err.messageAr : "تعذر حفظ الإعدادات.",
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Protected active="/settings">
      <PageHeader
        title="الإعدادات"
        subtitle="بيانات المدرسة والعملة واللغة وحدود التشغيل."
        action={
          isAdmin ? (
            <Link href="/settings/users" className="fd-btn fd-btn-secondary">
              <UsersRound size={16} aria-hidden />
              إدارة المستخدمين
            </Link>
          ) : undefined
        }
      />

      <Link
        href="/settings/templates"
        className="fd-card mb-4 flex min-h-11 items-center justify-between gap-3 px-5 py-4 transition hover:bg-[var(--fd-surface-alt)]"
      >
        <span className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--fd-brand-soft)] text-[var(--fd-brand)]">
            <BookText size={17} aria-hidden />
          </span>
          <span className="min-w-0">
            <span className="block text-[13px] font-semibold text-[var(--fd-ink)]">
              قوالب الرسائل
            </span>
            <span className="mt-0.5 block text-[11px] text-[var(--fd-ink-muted)]">
              نصوص رسائل التذكير وإصداراتها.
            </span>
          </span>
        </span>
        <span className="text-[12px] font-medium text-[var(--fd-brand)]">عرض</span>
      </Link>

      {message && (
        <p
          role={message.kind === "error" ? "alert" : "status"}
          className={`mb-4 rounded-[var(--fd-radius-control)] px-3 py-2 text-[12px] ${
            message.kind === "success"
              ? "bg-[var(--fd-green-soft)] text-[var(--fd-green-text)]"
              : "bg-[var(--fd-red-soft)] text-[var(--fd-red-text)]"
          }`}
        >
          {message.text}
        </p>
      )}

      {!form ? (
        <div className="fd-card fd-card-pad space-y-4">
          <div className="fd-skeleton h-10 w-full" />
          <div className="fd-skeleton h-10 w-full" />
          <div className="fd-skeleton h-10 w-full" />
        </div>
      ) : (
        <form onSubmit={onSubmit} className="fd-card fd-card-pad">
          <div className="grid gap-5 md:grid-cols-2">
            <div className="md:col-span-2">
              <label htmlFor="school_name" className="fd-label">
                اسم المدرسة
              </label>
              <input
                id="school_name"
                className="fd-input"
                value={form.school_name}
                onChange={(event) => update("school_name", event.target.value)}
                disabled={!isAdmin || saving}
                required
              />
            </div>

            <div>
              <label htmlFor="default_currency" className="fd-label">
                رمز العملة (ISO)
              </label>
              <input
                id="default_currency"
                className="fd-input text-left"
                dir="ltr"
                maxLength={3}
                value={form.default_currency}
                onChange={(event) => update("default_currency", event.target.value.toUpperCase())}
                disabled={!isAdmin || saving}
                required
              />
            </div>

            <div>
              <label htmlFor="currency_symbol" className="fd-label">
                رمز العملة في الواجهة
              </label>
              <input
                id="currency_symbol"
                className="fd-input"
                value={form.currency_symbol}
                placeholder="مثال: د.س"
                onChange={(event) => update("currency_symbol", event.target.value)}
                disabled={!isAdmin || saving}
                required
              />
            </div>

            <div>
              <label htmlFor="timezone" className="fd-label">
                المنطقة الزمنية
              </label>
              <input
                id="timezone"
                className="fd-input text-left"
                dir="ltr"
                value={form.timezone}
                onChange={(event) => update("timezone", event.target.value)}
                disabled={!isAdmin || saving}
                required
              />
            </div>

            <div>
              <label htmlFor="locale" className="fd-label">
                اللغة
              </label>
              <input
                id="locale"
                className="fd-input text-left"
                dir="ltr"
                value={form.locale}
                onChange={(event) => update("locale", event.target.value)}
                disabled={!isAdmin || saving}
                required
              />
            </div>

            <div>
              <label htmlFor="contact_phone" className="fd-label">
                هاتف التواصل
              </label>
              <input
                id="contact_phone"
                className="fd-input text-left"
                dir="ltr"
                value={form.contact_phone ?? ""}
                onChange={(event) => update("contact_phone", event.target.value)}
                disabled={!isAdmin || saving}
              />
            </div>

            <div>
              <label htmlFor="contact_email" className="fd-label">
                بريد التواصل
              </label>
              <input
                id="contact_email"
                type="email"
                className="fd-input text-left"
                dir="ltr"
                value={form.contact_email ?? ""}
                onChange={(event) => update("contact_email", event.target.value)}
                disabled={!isAdmin || saving}
              />
            </div>

            <div>
              <label htmlFor="send_limit" className="fd-label">
                الحد الأقصى للإرسال
              </label>
              <input
                id="send_limit"
                type="number"
                min={1}
                max={10000}
                className="fd-input text-left"
                dir="ltr"
                value={form.send_limit}
                onChange={(event) => update("send_limit", Number(event.target.value))}
                disabled={!isAdmin || saving}
              />
            </div>

            <div>
              <label htmlFor="batch_limit" className="fd-label">
                حد الدفعة
              </label>
              <input
                id="batch_limit"
                type="number"
                min={1}
                max={10000}
                className="fd-input text-left"
                dir="ltr"
                value={form.batch_limit}
                onChange={(event) => update("batch_limit", Number(event.target.value))}
                disabled={!isAdmin || saving}
              />
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--fd-line)] pt-5">
            <p className="text-[11px] leading-5 text-[var(--fd-ink-subtle)]">
              تُحفظ العملة كرمز ISO، ويُستخدم رمز العرض في الواجهة والرسائل.
            </p>
            {isAdmin ? (
              <button type="submit" className="fd-btn fd-btn-primary" disabled={saving}>
                <Save size={16} aria-hidden />
                {saving ? "جارٍ الحفظ..." : "حفظ الإعدادات"}
              </button>
            ) : (
              <p className="text-[12px] text-[var(--fd-ink-muted)]">العرض فقط — التعديل متاح لمدير النظام.</p>
            )}
          </div>
        </form>
      )}

      {/* Admin-only: never mounted for staff, and it needs no extra permission. */}
      {isAdmin && (
        <MessagingProviderPanel locale={form?.locale} timeZone={form?.timezone} />
      )}
    </Protected>
  );
}
