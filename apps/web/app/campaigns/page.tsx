import type { CampaignStatus } from "@/lib/api";
import { CampaignsListView } from "@/components/campaigns/CampaignsListView";

const STATUSES = new Set<string>([
  "draft",
  "awaiting_approval",
  "approved",
  "cancelled",
]);

export default async function CampaignsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string | string[] }>;
}) {
  const params = await searchParams;
  const raw = typeof params.status === "string" ? params.status : "";
  const status = (STATUSES.has(raw) ? raw : "") as CampaignStatus | "";

  return <CampaignsListView status={status} />;
}
