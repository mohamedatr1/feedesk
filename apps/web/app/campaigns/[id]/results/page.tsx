import { CampaignResultsView } from "@/components/campaigns/CampaignResultsView";

export default async function CampaignResultsPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ page?: string | string[] }>;
}) {
  const { id } = await params;
  const query = await searchParams;
  const rawPage = typeof query.page === "string" ? Number(query.page) : NaN;
  const page = Number.isFinite(rawPage) && rawPage >= 1 ? Math.floor(rawPage) : 1;

  return <CampaignResultsView campaignId={id} page={page} />;
}
