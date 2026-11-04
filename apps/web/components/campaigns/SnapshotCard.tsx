import { Lock } from "lucide-react";
import { formatDateTime, formatNumber } from "@/lib/api";
import type { CampaignDetail } from "@/lib/api";
import { CampaignStatusPill } from "@/components/campaigns/CampaignStatusPill";
import { CurrencyTotals } from "@/components/imports/CurrencyTotals";
import { SnapshotHash } from "@/components/campaigns/SnapshotHash";

export function SnapshotCard({
  campaign,
  locale,
  timeZone,
  muted = false,
}: {
  campaign: CampaignDetail;
  locale?: string | null;
  timeZone?: string | null;
  muted?: boolean;
}) {
  return (
    <section
      className={`rounded-[var(--fd-radius-card)] border p-5 ${
        muted
          ? "border-[var(--fd-line)] bg-[var(--fd-surface-alt)]"
          : "border-[var(--fd-green)]/30 bg-[var(--fd-green-soft)]"
      }`}
      aria-labelledby="snapshot-title"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <Lock
            size={18}
            className={`mt-0.5 shrink-0 ${
              muted ? "text-[var(--fd-ink-muted)]" : "text-[var(--fd-green-text)]"
            }`}
            aria-hidden
          />
          <div className="min-w-0">
            <h2
              id="snapshot-title"
              className="text-[15px] font-bold text-[var(--fd-ink)]"
            >
              نسخة معتمدة ومقفلة
            </h2>
            <p className="mt-1 text-[13px] text-[var(--fd-ink-muted)]">
              اعتُمدت في{" "}
              <bdi dir="ltr">
                {campaign.approved_at
                  ? formatDateTime(campaign.approved_at, { locale, timeZone })
                  : "—"}
              </bdi>
              {campaign.approved_by_name && (
                <>
                  {" "}
                  بواسطة <bdi dir="auto">{campaign.approved_by_name}</bdi>
                </>
              )}
              .
            </p>
            <div className="mt-1 text-[12px] text-[var(--fd-ink-muted)]">
              المستلمون المثبّتون:{" "}
              <span className="font-semibold tabular-nums text-[var(--fd-ink)]">
                {formatNumber(campaign.recipient_count)}
              </span>
              {Object.keys(campaign.totals_by_currency ?? {}).length > 0 && (
                <>
                  {" · "}الإجماليات:
                  <CurrencyTotals
                    totals={campaign.totals_by_currency}
                    className="mt-1"
                  />
                </>
              )}
            </div>
            <p className="mt-2 text-[12px] font-medium text-[var(--fd-ink)]">
              لا يمكن تعديل هذه الحملة أو مستلميها.
            </p>
          </div>
        </div>
        <CampaignStatusPill status={campaign.status} />
      </div>

      {campaign.snapshot_hash && <SnapshotHash hash={campaign.snapshot_hash} />}
    </section>
  );
}
