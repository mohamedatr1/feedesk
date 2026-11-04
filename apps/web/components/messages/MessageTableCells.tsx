import { ArrowUpLeft } from "lucide-react";
import Link from "next/link";
import { MessageStatusPill } from "@/components/messages/MessageStatusPill";
import {
  messageSecondLine,
  middleTruncate,
  formatMessageMoney,
} from "@/components/messages/message-format";
import { type MessageSummary } from "@/lib/api";

export function MessageStatusCell({
  message,
  formatted,
}: {
  message: MessageSummary;
  formatted: (value: string | null) => string;
}) {
  return (
    <>
      <MessageStatusPill status={message.internal_status} />
      <p className="mt-1 line-clamp-1 text-[10px] text-[var(--fd-ink-subtle)]">
        {messageSecondLine(message, formatted)}
      </p>
    </>
  );
}

/** A 3px inline-start marker for failed/unknown rows: never colour-only. */
export function RowReviewMarker({ status }: { status: string }) {
  if (status !== "failed" && status !== "unknown") return null;
  return (
    <span
      aria-hidden
      className={`absolute inset-y-0 start-0 w-[3px] ${
        status === "failed" ? "bg-[var(--fd-red)]" : "bg-[var(--fd-amber)]"
      }`}
    />
  );
}

export function MessageRowAction({
  message,
  variant,
}: {
  message: MessageSummary;
  variant: "history" | "results";
}) {
  return (
    <Link
      href={`/messages/${message.id}`}
      className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
      aria-label={
        variant === "history"
          ? `عرض رسالة ${message.guardian_name} في حملة ${message.campaign_name}`
          : `عرض رسالة ${message.guardian_name}`
      }
    >
      <ArrowUpLeft size={14} aria-hidden />
      عرض
    </Link>
  );
}

export function MessageGuardianCell({
  message,
  secondLine,
  formatted,
}: {
  message: MessageSummary;
  secondLine: "campaign" | "created" | "none";
  formatted?: (value: string | null) => string;
}) {
  return (
    <>
      <Link
        href={`/messages/${message.id}`}
        className="block truncate text-[13px] font-medium text-[var(--fd-ink)] hover:text-[var(--fd-brand)] hover:underline"
      >
        <bdi dir="auto">{message.guardian_name}</bdi>
      </Link>
      {secondLine === "campaign" && (
        <p className="mt-0.5 truncate text-[10px] text-[var(--fd-ink-subtle)]">
          الحملة:{" "}
          <Link href={`/campaigns/${message.campaign_id}`} className="hover:underline">
            <bdi dir="auto">{message.campaign_name}</bdi>
          </Link>
        </p>
      )}
      {secondLine === "created" && formatted && (
        <p className="mt-0.5 truncate text-[10px] text-[var(--fd-ink-subtle)]">
          أُنشئت <bdi dir="ltr">{formatted(message.created_at)}</bdi>
        </p>
      )}
    </>
  );
}

export function MessagePhoneCell({ message }: { message: MessageSummary }) {
  return (
    <bdi dir="ltr" className="whitespace-nowrap font-mono text-[12px]">
      {message.destination_phone_masked}
    </bdi>
  );
}

export function MessageAmountCell({ message }: { message: MessageSummary }) {
  const value = formatMessageMoney(message.amount, message.currency);
  return (
    <bdi dir="ltr" className="whitespace-nowrap tabular-nums text-[12px]">
      {value}
    </bdi>
  );
}

export function MessageUpdatedCell({
  message,
  formatted,
}: {
  message: MessageSummary;
  formatted: (value: string | null) => string;
}) {
  return (
    <>
      <bdi dir="ltr" className="whitespace-nowrap tabular-nums">
        {formatted(message.updated_at)}
      </bdi>
      <p className="mt-0.5 whitespace-nowrap text-[10px] text-[var(--fd-ink-subtle)]">
        أُنشئت <bdi dir="ltr">{formatted(message.created_at)}</bdi>
      </p>
    </>
  );
}

export function MessageProviderRefCell({ message }: { message: MessageSummary }) {
  if (!message.provider_message_id) {
    return <span className="text-[var(--fd-ink-subtle)]">—</span>;
  }
  return (
    <bdi
      dir="ltr"
      lang="en"
      className="whitespace-nowrap font-mono text-[11px] text-[var(--fd-ink-muted)]"
    >
      {middleTruncate(message.provider_message_id)}
    </bdi>
  );
}
