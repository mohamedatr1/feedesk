import Link from "next/link";
import { formatDateTime } from "@/lib/api";
import type { CampaignDetail } from "@/lib/api";

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2 border-b border-[var(--fd-line)] py-2 last:border-b-0">
      <dt className="text-[11px] text-[var(--fd-ink-subtle)]">{label}</dt>
      <dd className="min-w-0 text-[12px] text-[var(--fd-ink)]">{children}</dd>
    </div>
  );
}

export function CampaignFacts({
  campaign,
  locale,
  timeZone,
}: {
  campaign: CampaignDetail;
  locale?: string | null;
  timeZone?: string | null;
}) {
  const approved = campaign.status === "approved";
  const formatted = (value: string | null) =>
    value ? formatDateTime(value, { locale, timeZone }) : "—";

  return (
    <section className="fd-card fd-card-pad" aria-labelledby="campaign-facts-title">
      <h2
        id="campaign-facts-title"
        className="mb-2 text-sm font-semibold text-[var(--fd-ink)]"
      >
        بيانات الحملة
      </h2>
      <dl>
        <Row label="المصدر">
          {campaign.source_import_id ? (
            <Link
              href={`/statements/${campaign.source_import_id}`}
              className="text-[var(--fd-brand)] hover:underline"
            >
              <bdi dir="auto">{campaign.source_filename ?? "الكشف"}</bdi>
            </Link>
          ) : (
            "—"
          )}
          {approved && (
            <span className="mt-0.5 block text-[11px] text-[var(--fd-ink-subtle)]">
              تعديلات الكشف بعد الاعتماد لا تغيّر هذه النسخة.
            </span>
          )}
        </Row>
        <Row label="القالب">
          {campaign.template_name ? (
            <>
              <bdi dir="auto">{campaign.template_name}</bdi>
              {campaign.template_version != null && (
                <span className="text-[var(--fd-ink-muted)]">
                  {" "}
                  · الإصدار {campaign.template_version}
                </span>
              )}
            </>
          ) : (
            "—"
          )}
        </Row>
        <Row label="أُنشئت">
          <bdi dir="ltr">{formatted(campaign.created_at)}</bdi>
          {campaign.created_by_name && (
            <span className="text-[var(--fd-ink-muted)]">
              {" "}
              · <bdi dir="auto">{campaign.created_by_name}</bdi>
            </span>
          )}
        </Row>
        <Row label="أُرسلت للاعتماد">
          <bdi dir="ltr">{formatted(campaign.submitted_at)}</bdi>
        </Row>
        {!approved && (
          <Row label="آخر معاينة">
            <bdi dir="ltr">{formatted(campaign.previewed_at)}</bdi>
          </Row>
        )}
        <Row label="اعتُمدت">
          {campaign.approved_at ? (
            <>
              <bdi dir="ltr">{formatted(campaign.approved_at)}</bdi>
              {campaign.approved_by_name && (
                <span className="text-[var(--fd-ink-muted)]">
                  {" "}
                  · <bdi dir="auto">{campaign.approved_by_name}</bdi>
                </span>
              )}
            </>
          ) : (
            "—"
          )}
        </Row>
      </dl>
    </section>
  );
}
