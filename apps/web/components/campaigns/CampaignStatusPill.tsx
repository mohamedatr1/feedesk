import { StatusPill } from "@/components/StatusPill";
import { CAMPAIGN_STATUS_META } from "@/components/campaigns/campaign-format";

export function CampaignStatusPill({ status }: { status: string }) {
  const meta = CAMPAIGN_STATUS_META[status];
  return <StatusPill tone={meta?.tone ?? "neutral"}>{meta?.label ?? "—"}</StatusPill>;
}
