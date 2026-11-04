import Link from "next/link";
import { Inbox } from "lucide-react";
import { type DashboardActivityItem } from "@/lib/api";
import { EmptyState } from "@/components/EmptyState";
import { StatusPill } from "@/components/StatusPill";
import {
  activityActionLabel,
  activityEntityLabel,
  activityStatusMeta,
  shortId,
} from "@/components/activity/activity-format";

/**
 * The dashboard's activity window. Only the fields the contract exposes are
 * rendered: no audit payloads, no entity payloads, no full ids.
 */
export function ActivityTable({
  items,
  isAdmin,
  formatted,
}: {
  items: DashboardActivityItem[];
  isAdmin: boolean;
  formatted: (value: string | null) => string;
}) {
  return (
    <section
      className="fd-card mt-5 overflow-hidden"
      aria-labelledby="dashboard-activity-title"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--fd-line)] px-5 py-4">
        <div className="flex items-center gap-2">
          <span aria-hidden className="h-4 w-1 rounded-full bg-[var(--fd-brand)]" />
          <h2
            id="dashboard-activity-title"
            className="text-[15px] font-bold text-[var(--fd-ink)]"
          >
            آخر النشاطات
          </h2>
        </div>
        {isAdmin && (
          <Link
            href="/audit"
            className="inline-flex h-11 items-center gap-1 px-2 text-[12px] font-medium text-[var(--fd-brand)] hover:underline"
          >
            عرض الكل
          </Link>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="fd-table min-w-[760px]">
          <caption className="sr-only">آخر النشاطات الإدارية، الأحدث أولًا</caption>
          <thead>
            <tr>
              <th scope="col" className="min-w-[220px]">
                العملية
              </th>
              <th scope="col">المستخدم</th>
              <th scope="col">الكيان</th>
              <th scope="col">الحالة</th>
              <th scope="col" className="whitespace-nowrap">
                التاريخ والوقت
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((event) => {
              const label = activityActionLabel(event.action);
              const status = activityStatusMeta(event.status);
              const actor = event.actor_name || shortId(event.actor_user_id);

              return (
                <tr
                  key={event.id}
                  className="min-h-[52px] hover:bg-[var(--fd-surface-alt)] focus-within:bg-[var(--fd-brand-soft)]/40"
                >
                  <th
                    scope="row"
                    className="bg-transparent text-right align-middle text-[13px] font-normal text-[var(--fd-ink)]"
                  >
                    {label ? (
                      <>
                        <p className="font-medium">{label}</p>
                        <p
                          className="mt-0.5 font-mono text-[10px] text-[var(--fd-ink-subtle)]"
                          dir="ltr"
                        >
                          {event.action}
                        </p>
                      </>
                    ) : (
                      <bdi
                        dir="ltr"
                        className="break-all font-mono text-[11px] text-[var(--fd-ink-muted)]"
                      >
                        {event.action || "—"}
                      </bdi>
                    )}
                  </th>

                  <td className="align-middle text-[12px]">
                    {actor ? <bdi dir="auto">{actor}</bdi> : <span className="text-[var(--fd-ink-subtle)]">—</span>}
                  </td>

                  <td className="align-middle">
                    <bdi dir="auto" className="text-[12px] text-[var(--fd-ink)]">
                      {activityEntityLabel(event.entity_type)}
                    </bdi>
                    {event.entity_id && (
                      <p
                        className="mt-0.5 font-mono text-[10px] text-[var(--fd-ink-subtle)]"
                        dir="ltr"
                      >
                        {shortId(event.entity_id)}
                      </p>
                    )}
                  </td>

                  <td className="align-middle">
                    {status ? (
                      <StatusPill tone={status.tone}>{status.label}</StatusPill>
                    ) : event.status ? (
                      <StatusPill tone="neutral">
                        <bdi dir="auto">{event.status}</bdi>
                      </StatusPill>
                    ) : (
                      <span className="text-[var(--fd-ink-subtle)]">—</span>
                    )}
                  </td>

                  <td className="whitespace-nowrap align-middle text-[12px] tabular-nums">
                    <bdi dir="ltr">{formatted(event.created_at)}</bdi>
                  </td>
                </tr>
              );
            })}

            {items.length === 0 && (
              <tr>
                <td colSpan={5}>
                  <EmptyState
                    icon={Inbox}
                    title="لا توجد نشاطات بعد"
                    description="ستظهر هنا عمليات الاستيراد والحملات والرسائل بعد بدء العمل."
                    action={
                      <Link href="/statements/upload" className="fd-btn fd-btn-secondary h-11">
                        رفع كشوف جديدة
                      </Link>
                    }
                  />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
