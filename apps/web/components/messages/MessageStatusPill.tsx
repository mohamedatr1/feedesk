import { StatusPill } from "@/components/StatusPill";
import { MESSAGE_STATUS_META } from "@/components/messages/message-format";

export function MessageStatusPill({ status }: { status: string }) {
  const meta = MESSAGE_STATUS_META[status];
  return <StatusPill tone={meta?.tone ?? "neutral"}>{meta?.label ?? "—"}</StatusPill>;
}
