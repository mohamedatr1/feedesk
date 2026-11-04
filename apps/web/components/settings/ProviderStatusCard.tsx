import { Lock, ShieldCheck, Trash } from "lucide-react";
import { formatDateTime } from "@/lib/api";
import type { MessagingProviderStatus } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";
import { channelLabel, credentialSourceLabel, testModeLabel } from "./provider-format";

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-medium text-[var(--fd-ink-subtle)]">{label}</dt>
      <dd className="mt-1 text-[13px] font-semibold leading-6 text-[var(--fd-ink)]">
        {children}
      </dd>
    </div>
  );
}

export function ProviderStatusCard({
  status,
  locale,
  timeZone,
  onRevoke,
  revokeBusy = false,
}: {
  status: MessagingProviderStatus;
  locale?: string | null;
  timeZone?: string | null;
  onRevoke: () => void;
  revokeBusy?: boolean;
}) {
  const liveBlocked = !status.live_send_available;

  return (
    <section className="fd-card overflow-hidden" aria-labelledby="provider-status-title">
      <div className="border-b border-[var(--fd-line)] bg-[var(--fd-surface-alt)] px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 id="provider-status-title" className="text-sm font-semibold text-[var(--fd-ink)]">
              حالة الاتصال
            </h3>
            <p className="mt-0.5 text-[11px] leading-5 text-[var(--fd-ink-muted)]">
              آخر حالة معروفة من الخادم. لا يُعاد المفتاح ولا يُعرض في هذه الصفحة.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill tone={status.configured ? "green" : "red"}>
              {status.configured ? "بيانات الاعتماد مهيّأة" : "غير مهيّأ"}
            </StatusPill>
            <StatusPill tone="neutral">
              <bdi dir="ltr">{status.provider || "—"}</bdi>
            </StatusPill>
          </div>
        </div>
      </div>

      <div className="space-y-4 px-5 py-4">
        {status.credential_error && (
          <p
            role="alert"
            className="rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] leading-5 text-[var(--fd-red-text)]"
          >
            <span className="font-semibold">خطأ في بيانات الاعتماد: </span>
            <bdi dir="auto">{status.credential_error}</bdi>
          </p>
        )}

        <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2 xl:grid-cols-4">
          <Fact label="المزوّد">
            <bdi dir="ltr">{status.provider || "—"}</bdi>
          </Fact>
          <Fact label="القناة">{channelLabel(status.channel)}</Fact>
          <Fact label="معرّف المرسل">
            {status.sender_id ? <bdi dir="ltr">{status.sender_id}</bdi> : "—"}
          </Fact>
          <Fact label="مصدر بيانات الاعتماد">
            {credentialSourceLabel(status.credential_source)}
          </Fact>
          <Fact label="إصدار المفتاح">
            {status.key_version != null ? `الإصدار ${status.key_version}` : "—"}
          </Fact>
          <Fact label="وضع الاختبار">{testModeLabel(status.test_send_mode)}</Fact>
          <Fact label="آخر تدوير">
            {status.rotated_at ? (
              <>
                <bdi dir="ltr">
                  {formatDateTime(status.rotated_at, { locale, timeZone })}
                </bdi>
                {status.rotated_by_name && (
                  <span className="mt-0.5 block text-[11px] font-normal text-[var(--fd-ink-muted)]">
                    بواسطة <bdi dir="auto">{status.rotated_by_name}</bdi>
                  </span>
                )}
              </>
            ) : (
              "—"
            )}
          </Fact>
          <Fact label="الإرسال الفعلي">
            <span
              className={
                liveBlocked ? "text-[var(--fd-amber-text)]" : "text-[var(--fd-green-text)]"
              }
            >
              {liveBlocked ? "محجوب" : "متاح"}
            </span>
          </Fact>
        </dl>

        <div
          className={`relative overflow-hidden rounded-[var(--fd-radius-control)] py-2.5 pe-3 ps-4 ${
            liveBlocked
              ? "bg-[var(--fd-amber-soft)] text-[var(--fd-amber-text)]"
              : "bg-[var(--fd-green-soft)] text-[var(--fd-green-text)]"
          }`}
        >
          <span
            aria-hidden
            className={`absolute inset-y-0 start-0 w-[3px] ${
              liveBlocked ? "bg-[var(--fd-amber)]" : "bg-[var(--fd-green)]"
            }`}
          />
          <div className="flex items-start gap-2">
            {liveBlocked ? (
              <Lock size={15} className="mt-0.5 shrink-0" aria-hidden />
            ) : (
              <ShieldCheck size={15} className="mt-0.5 shrink-0" aria-hidden />
            )}
            <div className="min-w-0">
              <p className="text-[12px] font-semibold">
                {liveBlocked
                  ? "الإرسال الفعلي محجوب حتى اعتماد G0/G4"
                  : "الإرسال الفعلي متاح"}
              </p>
              <p className="mt-0.5 text-[11px] leading-5">
                {liveBlocked
                  ? "يبقى إرسال الاختبار في الوضع التجريبي، ولا تخرج أي رسالة حقيقية إلى أولياء الأمور."
                  : "أي إرسال يبقى خاضعًا لحدود التشغيل وقائمة السماح المعتمدة."}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--fd-line)] px-5 py-3">
        <p className="text-[11px] leading-5 text-[var(--fd-ink-subtle)]">
          إبطال الاعتماد يوقف الإرسال والتحقق من الرصيد حتى حفظ مفتاح جديد.
        </p>
        <button
          type="button"
          onClick={onRevoke}
          disabled={!status.configured || revokeBusy}
          className="fd-btn fd-btn-ghost h-11 text-[var(--fd-red-text)] hover:bg-[var(--fd-red-soft)]"
          title={
            status.configured
              ? "إبطال بيانات الاعتماد الحالية"
              : "لا توجد بيانات اعتماد لإبطالها."
          }
        >
          <Trash size={15} aria-hidden />
          إبطال بيانات الاعتماد
        </button>
      </div>
    </section>
  );
}
