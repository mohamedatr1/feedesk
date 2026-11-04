import { MessageDetailView } from "@/components/messages/MessageDetailView";

export default async function MessageDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <MessageDetailView messageId={id} />;
}
