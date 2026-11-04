import { CampaignDetailView } from "@/components/campaigns/CampaignDetailView";

export default async function CampaignDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ created?: string | string[] }>;
}) {
  const { id } = await params;
  const query = await searchParams;
  const justCreated = query.created === "1";

  return <CampaignDetailView campaignId={id} justCreated={justCreated} />;
}
