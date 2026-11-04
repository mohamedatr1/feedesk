import Link from "next/link";
import { type MessageSummary } from "@/lib/api";
import {
  MessageAmountCell,
  MessageGuardianCell,
  MessagePhoneCell,
  MessageProviderRefCell,
  MessageRowAction,
  MessageStatusCell,
  MessageUpdatedCell,
} from "@/components/messages/MessageTableCells";
import { formatMessageMoney, messageSecondLine } from "@/components/messages/message-format";
import { MessageStatusPill } from "@/components/messages/MessageStatusPill";

export type MessageTableVariant = "history" | "results";

function reviewRowClass(status: string): string {
  if (status === "failed") return "border-s-[3px] border-s-[var(--fd-red)]";
  if (status === "unknown") return "border-s-[3px] border-s-[var(--fd-amber)]";
  return "";
}

export function MessageTable({
  messages,
  loading = false,
  variant = "history",
  caption,
  formatted,
}: {
  messages: MessageSummary[];
  loading?: boolean;
  variant?: MessageTableVariant;
  caption: string;
  formatted: (value: string | null) => string;
}) {
  const showCampaignColumn = variant === "history";
  const columnCount = showCampaignColumn ? 8 : 6;

  return (
    <>
      <div className="hidden overflow-x-auto lg:block">
        <table className="fd-table min-w-[820px]" aria-busy={loading}>
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr>
              <th scope="col" className="min-w-[200px]">المستلم</th>
              {showCampaignColumn && (
                <th scope="col" className="hidden min-[1360px]:table-cell">الحملة</th>
              )}
              <th scope="col">الهاتف</th>
              <th scope="col">المبلغ</th>
              <th scope="col">الحالة</th>
              {showCampaignColumn && (
                <th scope="col" className="hidden min-[1360px]:table-cell">
                  مرجع المزوّد
                </th>
              )}
              <th scope="col">آخر تحديث</th>
              <th scope="col" className="w-[1%] whitespace-nowrap">
                <span className="sr-only">الإجراءات</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {loading &&
              messages.length === 0 &&
              Array.from({ length: 6 }).map((_, index) => (
                <tr key={`skeleton-${index}`}>
                  <td colSpan={columnCount}>
                    <div className="fd-skeleton h-8 w-full" />
                  </td>
                </tr>
              ))}

            {messages.map((message) => (
              <tr
                key={message.id}
                className={`min-h-[64px] hover:bg-[var(--fd-surface-alt)] focus-within:bg-[var(--fd-brand-soft)]/40 ${reviewRowClass(
                  message.internal_status,
                )}`}
              >
                <th
                  scope="row"
                  className="min-w-[200px] max-w-[240px] bg-transparent text-right align-top text-[13px] font-normal text-[var(--fd-ink)]"
                >
                  <MessageGuardianCell
                    message={message}
                    secondLine={
                      showCampaignColumn ? "none" : variant === "results" ? "created" : "campaign"
                    }
                    formatted={formatted}
                  />
                </th>
                {showCampaignColumn && (
                  <td className="hidden max-w-[170px] truncate align-top min-[1360px]:table-cell">
                    <Link
                      href={`/campaigns/${message.campaign_id}`}
                      className="text-[12px] hover:text-[var(--fd-brand)] hover:underline"
                    >
                      <bdi dir="auto">{message.campaign_name}</bdi>
                    </Link>
                  </td>
                )}
                <td className="whitespace-nowrap align-top">
                  <MessagePhoneCell message={message} />
                </td>
                <td className="whitespace-nowrap align-top">
                  <MessageAmountCell message={message} />
                </td>
                <td className="align-top">
                  <MessageStatusCell message={message} formatted={formatted} />
                </td>
                {showCampaignColumn && (
                  <td className="hidden align-top min-[1360px]:table-cell">
                    <MessageProviderRefCell message={message} />
                  </td>
                )}
                <td className="whitespace-nowrap align-top">
                  <MessageUpdatedCell message={message} formatted={formatted} />
                </td>
                <td className="align-top">
                  <MessageRowAction message={message} variant={variant} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="space-y-3 p-4 lg:hidden">
        {loading &&
          messages.length === 0 &&
          Array.from({ length: 4 }).map((_, index) => (
            <li key={`skeleton-card-${index}`} className="fd-skeleton h-40 w-full" />
          ))}

        {messages.map((message) => (
          <li
            key={message.id}
            className={`rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] p-4 ${reviewRowClass(
              message.internal_status,
            )}`}
          >
            <div className="flex items-start justify-between gap-3">
              <Link
                href={`/messages/${message.id}`}
                className="min-w-0 truncate text-[13px] font-medium text-[var(--fd-ink)] hover:text-[var(--fd-brand)] hover:underline"
              >
                <bdi dir="auto">{message.guardian_name}</bdi>
              </Link>
              <MessageStatusPill status={message.internal_status} />
            </div>
            <p className="mt-1 truncate text-[11px] text-[var(--fd-ink-subtle)]">
              الحملة:{" "}
              <Link href={`/campaigns/${message.campaign_id}`} className="hover:underline">
                <bdi dir="auto">{message.campaign_name}</bdi>
              </Link>
            </p>
            <p className="mt-0.5 text-[11px] text-[var(--fd-ink-muted)]">
              {messageSecondLine(message, formatted)}
            </p>
            <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[12px]">
              <div>
                <dt className="text-[10px] text-[var(--fd-ink-subtle)]">الهاتف</dt>
                <dd>
                  <bdi dir="ltr" className="whitespace-nowrap font-mono text-[11px]">
                    {message.destination_phone_masked}
                  </bdi>
                </dd>
              </div>
              <div>
                <dt className="text-[10px] text-[var(--fd-ink-subtle)]">المبلغ</dt>
                <dd>
                  <bdi dir="ltr" className="whitespace-nowrap tabular-nums">
                    {formatMessageMoney(message.amount, message.currency)}
                  </bdi>
                </dd>
              </div>
              <div>
                <dt className="text-[10px] text-[var(--fd-ink-subtle)]">آخر تحديث</dt>
                <dd>
                  <bdi dir="ltr" className="whitespace-nowrap tabular-nums">
                    {formatted(message.updated_at)}
                  </bdi>
                </dd>
              </div>
              <div>
                <dt className="text-[10px] text-[var(--fd-ink-subtle)]">أُنشئت</dt>
                <dd>
                  <bdi dir="ltr" className="whitespace-nowrap tabular-nums">
                    {formatted(message.created_at)}
                  </bdi>
                </dd>
              </div>
            </dl>
            <div className="mt-3">
              <Link
                href={`/messages/${message.id}`}
                className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                aria-label={`عرض رسالة ${message.guardian_name} في حملة ${message.campaign_name}`}
              >
                عرض الرسالة
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}
