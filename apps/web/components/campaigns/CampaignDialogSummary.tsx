import { formatDecimalString, formatNumber } from "@/lib/api";
import type { CampaignSummary } from "@/lib/api";

/** Label-first counts plus one line per currency. Never combines currencies. */
export function CampaignDialogSummary({ campaign }: { campaign: CampaignSummary }) {
  const totals = Object.entries(campaign.totals_by_currency ?? {})
    .filter(([, amount]) => typeof amount === "string" && amount.trim() !== "")
    .sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="flex flex-wrap items-start justify-between gap-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] p-3">
      <dl className="space-y-1 text-[12px] text-[var(--fd-ink-muted)]">
        <div>
          <dt className="sr-only">المستلمون</dt>
          <dd>
            المستلمون:{" "}
            <span className="font-semibold tabular-nums text-[var(--fd-ink)]">
              {formatNumber(campaign.recipient_count)}
            </span>
          </dd>
        </div>
        <div>
          <dt className="sr-only">مستثناة</dt>
          <dd>
            مستثناة:{" "}
            <span className="tabular-nums text-[var(--fd-ink)]">
              {formatNumber(campaign.excluded_count)}
            </span>
          </dd>
        </div>
        <div>
          <dt className="sr-only">التحذيرات</dt>
          <dd>
            التحذيرات:{" "}
            <span className="tabular-nums text-[var(--fd-ink)]">
              {formatNumber(campaign.warnings?.length ?? 0)}
            </span>
          </dd>
        </div>
      </dl>

      {totals.length > 0 && (
        <dl className="space-y-1 text-[12.5px] tabular-nums">
          {totals.map(([currency, amount]) => (
            <div key={currency} className="flex items-center gap-2">
              <dt className="sr-only">{currency}</dt>
              <dd>
                <bdi dir="ltr">
                  <span aria-hidden className="text-[11px] text-[var(--fd-ink-subtle)]">
                    {currency}{" "}
                  </span>
                  <span className="font-semibold text-[var(--fd-ink)]">
                    {formatDecimalString(amount)}
                  </span>
                </bdi>
              </dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
