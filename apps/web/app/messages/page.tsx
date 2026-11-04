import { MESSAGE_STATUSES, type MessageStatus } from "@/lib/api";
import { MessagesListView } from "@/components/messages/MessagesListView";

const STATUS_SET = new Set<string>(MESSAGE_STATUSES);

export default async function MessagesPage({
  searchParams,
}: {
  searchParams: Promise<{
    page?: string | string[];
    campaign_id?: string | string[];
    status?: string | string[];
    q?: string | string[];
  }>;
}) {
  const params = await searchParams;
  const rawPage = typeof params.page === "string" ? Number(params.page) : NaN;
  const page = Number.isFinite(rawPage) && rawPage >= 1 ? Math.floor(rawPage) : 1;
  const rawStatus = typeof params.status === "string" ? params.status : "";
  const status = (STATUS_SET.has(rawStatus) ? rawStatus : "") as MessageStatus | "";
  const campaignId = typeof params.campaign_id === "string" ? params.campaign_id : "";
  const q = typeof params.q === "string" ? params.q.trim().slice(0, 120) : "";

  return (
    <MessagesListView
      page={page}
      campaignId={campaignId}
      status={status}
      q={q}
    />
  );
}
