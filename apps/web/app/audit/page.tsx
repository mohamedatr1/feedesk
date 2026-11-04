"use client";

import { useCallback, useEffect, useState } from "react";
import { Inbox, RefreshCw } from "lucide-react";
import { ApiError, api, formatDateTime, formatNumber, type AuditEvent } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import {
  activityActionLabel,
  activityEntityLabel,
  shortId,
} from "@/components/activity/activity-format";

function AuditContent() {
  const { settings } = useSession();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [actors, setActors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    api
      .audit(1, 25)
      .then((data) => {
        if (!mounted) return;
        setEvents(data.items);
        setTotal(data.total);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setError(err instanceof ApiError ? err.messageAr : "تعذر تحميل سجل العمليات.");
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    // Admin-only page: use the users list to show actor names instead of raw IDs.
    api
      .listUsers()
      .then((users) => {
        if (!mounted) return;
        setActors(Object.fromEntries(users.map((user) => [user.id, user.username])));
      })
      .catch(() => undefined);

    return () => {
      mounted = false;
    };
  }, [reloadKey]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const subtitle = loading
    ? "سجل غير قابل للتعديل للمهام الإدارية."
    : `سجل غير قابل للتعديل للمهام الإدارية. إجمالي الأحداث: ${formatNumber(total)}.`;

  return (
    <>
      <PageHeader title="سجل العمليات" subtitle={subtitle} />

      {error ? (
        <div role="alert" className="fd-card fd-card-pad text-[13px] text-[var(--fd-red-text)]">
          {error}
        </div>
      ) : (
        <section className="fd-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="fd-table min-w-[720px]" aria-busy={loading}>
              <caption className="sr-only">سجل العمليات الإدارية، الأحدث أولاً</caption>
              <thead>
                <tr>
                  <th scope="col">العملية</th>
                  <th scope="col">المستخدم</th>
                  <th scope="col">الكيان</th>
                  <th scope="col">المعرّف</th>
                  <th scope="col">التاريخ والوقت</th>
                </tr>
              </thead>
              <tbody>
                {loading &&
                  Array.from({ length: 4 }).map((_, index) => (
                    <tr key={`skeleton-${index}`}>
                      <td colSpan={5}>
                        <div className="fd-skeleton h-6 w-full" />
                      </td>
                    </tr>
                  ))}

                {!loading &&
                  events.map((event) => {
                    const actorName =
                      (event.actor_user_id ? actors[event.actor_user_id] : null) ??
                      shortId(event.actor_user_id);
                    return (
                      <tr key={event.id}>
                        <td>
                          <p className="font-medium text-[var(--fd-ink)]">
                            {activityActionLabel(event.action) ?? event.action}
                          </p>
                          <p
                            className="font-mono text-[11px] text-[var(--fd-ink-subtle)]"
                            dir="ltr"
                          >
                            {event.action}
                          </p>
                        </td>
                        <td>
                          {actorName ? (
                            <bdi dir="ltr">{actorName}</bdi>
                          ) : (
                            <span className="text-[var(--fd-ink-subtle)]">—</span>
                          )}
                        </td>
                        <td>{activityEntityLabel(event.entity_type)}</td>
                        <td>
                          {event.entity_id ? (
                            <details>
                              <summary
                                className="cursor-pointer font-mono text-[11px] text-[var(--fd-ink-muted)]"
                                dir="ltr"
                              >
                                {shortId(event.entity_id)}
                              </summary>
                              <p
                                className="mt-1 break-all font-mono text-[11px] text-[var(--fd-ink-subtle)]"
                                dir="ltr"
                              >
                                {event.entity_id}
                              </p>
                            </details>
                          ) : (
                            <span className="text-[var(--fd-ink-subtle)]">—</span>
                          )}
                        </td>
                        <td className="whitespace-nowrap tabular-nums">
                          <bdi dir="ltr">
                            {formatDateTime(event.created_at, {
                              locale: settings?.locale,
                              timeZone: settings?.timezone,
                            })}
                          </bdi>
                        </td>
                      </tr>
                    );
                  })}

                {!loading && events.length === 0 && (
                  <tr>
                    <td colSpan={5}>
                      <EmptyState
                        icon={Inbox}
                        title="لا توجد أحداث بعد"
                        description="ستظهر هنا عمليات تسجيل الدخول، تعديل الإعدادات، وإدارة المستخدمين."
                      />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between gap-3 border-t border-[var(--fd-line)] px-5 py-3 text-[11px] text-[var(--fd-ink-subtle)]">
            <span>
              {loading
                ? "جارٍ تحميل الأحداث…"
                : `عرض ${formatNumber(events.length)} من ${formatNumber(total)}`}
            </span>
            <button
              type="button"
              onClick={reload}
              disabled={loading}
              className="fd-btn fd-btn-ghost h-11 px-3 text-[12px]"
            >
              <RefreshCw size={14} aria-hidden />
              تحديث
            </button>
          </div>
        </section>
      )}
    </>
  );
}

export default function AuditPage() {
  return (
    <Protected active="/audit" requireAdmin>
      <AuditContent />
    </Protected>
  );
}
