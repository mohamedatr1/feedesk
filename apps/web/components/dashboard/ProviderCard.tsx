import Link from "next/link";
import { AlertCircle } from "lucide-react";
import { StatusPill } from "@/components/StatusPill";

/**
 * Honest, deliberately static provider status for this milestone. The
 * dashboard contract carries no live provider state, so this card never
 * claims a live send and never invents a credential status.
 */
export function ProviderCard({ isAdmin }: { isAdmin: boolean }) {
  return (
    <section
      className="fd-card fd-card-pad flex flex-col"
      aria-labelledby="dashboard-provider-title"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id="dashboard-provider-title" className="text-[15px] font-bold text-[var(--fd-ink)]">
            حالة قناة الرسائل
          </h2>
          <p className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">بيئة التطوير · مزوّد تجريبي</p>
        </div>
        <StatusPill tone="amber">تجريبي</StatusPill>
      </div>

      <div className="mt-4 flex items-start gap-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] p-3">
        <AlertCircle size={17} className="mt-0.5 shrink-0 text-[var(--fd-amber-text)]" aria-hidden />
        <p className="text-[12px] leading-6 text-[var(--fd-amber-text)]">
          لا يوجد إرسال SMS حقيقي حتى اعتماد G0/G4. تُعالج رسائل الاختبار بمزوّد تجريبي فقط.
        </p>
      </div>

      <dl className="mt-4 space-y-2 text-[12px]">
        <div className="flex items-center justify-between gap-3">
          <dt className="text-[var(--fd-ink-subtle)]">القناة</dt>
          <dd className="font-medium text-[var(--fd-ink)]">SMS محلي (محاكاة)</dd>
        </div>
        <div className="flex items-center justify-between gap-3">
          <dt className="text-[var(--fd-ink-subtle)]">الإرسال الفعلي</dt>
          <dd className="font-medium text-[var(--fd-amber-text)]">غير مفعّل</dd>
        </div>
      </dl>

      {isAdmin && (
        <div className="mt-auto pt-4">
          <Link
            href="/settings"
            className="fd-btn fd-btn-secondary h-11 w-full text-[12px]"
          >
            إعدادات قناة الرسائل
          </Link>
        </div>
      )}
    </section>
  );
}
