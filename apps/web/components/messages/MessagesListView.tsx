"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FilterX, Lock, MessageSquare, RefreshCw } from "lucide-react";
import {
  ApiError,
  api,
  formatDateTime,
  formatNumber,
  type MessageSummary,
  type MessageStatus,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { TablePager } from "@/components/imports/TablePager";
import { HistoryNotice } from "@/components/messages/HistoryNotice";
import { MessageTable } from "@/components/messages/MessageTable";
import {
  MessagesFilterBar,
  type CampaignOption,
} from "@/components/messages/MessagesFilterBar";
import { messagesHref } from "@/components/messages/message-format";

const PAGE_SIZE = 20;

export function MessagesListView({
  page,
  campaignId,
  status,
  q,
}: {
  page: number;
  campaignId: string;
  status: MessageStatus | "";
  q: string;
}) {
  return (
    <Protected active="/messages">
      <MessagesListContent page={page} campaignId={campaignId} status={status} q={q} />
    </Protected>
  );
}

function MessagesListContent({
  page,
  campaignId,
  status,
  q,
}: {
  page: number;
  campaignId: string;
  status: MessageStatus | "";
  q: string;
}) {
  const { settings } = useSession();
  const router = useRouter();

  const [items, setItems] = useState<MessageSummary[] | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [clamped, setClamped] = useState(false);

  const [campaigns, setCampaigns] = useState<CampaignOption[]>([]);
  const [selectedCampaignName, setSelectedCampaignName] = useState<string | null>(null);

  const formatted = useCallback(
    (value: string | null) =>
      value
        ? formatDateTime(value, { locale: settings?.locale, timeZone: settings?.timezone })
        : "—",
    [settings?.locale, settings?.timezone],
  );

  // Campaign picker: newest 50. A campaign outside that page still resolves by
  // id so the reader never sees a selection they cannot read.
  useEffect(() => {
    let mounted = true;
    api
      .listCampaigns({ page: 1, page_size: 50 })
      .then((data) => {
        if (!mounted) return;
        const list = (data.items ?? []).map((campaign) => ({
          id: campaign.id,
          name: campaign.name,
          date: campaign.created_at ? campaign.created_at.slice(0, 10) : null,
        }));
        setCampaigns(list);
        const match = list.find((item) => item.id === campaignId);
        if (match) setSelectedCampaignName(match.name);
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, [campaignId]);

  useEffect(() => {
    if (!campaignId) {
      setSelectedCampaignName(null);
      return;
    }
    let mounted = true;
    api
      .getCampaign(campaignId)
      .then((campaign) => {
        if (mounted) setSelectedCampaignName(campaign.name);
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, [campaignId]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    setSessionExpired(false);
    setForbidden(false);
    setClamped(false);

    api
      .listMessages({
        page,
        page_size: PAGE_SIZE,
        campaign_id: campaignId || undefined,
        status,
        q: q || undefined,
      })
      .then((data) => {
        if (!mounted) return;
        const nextItems = data.items ?? [];
        setItems(nextItems);
        setTotal(data.total ?? 0);
        setClamped(false);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 401) {
          setSessionExpired(true);
        } else if (err instanceof ApiError && err.status === 403) {
          setForbidden(true);
        } else {
          setError(err instanceof ApiError ? err.messageAr : "تعذر تحميل الرسائل.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [page, campaignId, status, q, reloadKey]);

  // A stale page link never leaves an empty table with total > 0.
  useEffect(() => {
    if (!items) return;
    if (items.length === 0 && total > 0 && page > 1) {
      const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));
      if (page !== lastPage) {
        router.replace(messagesHref({ campaign_id: campaignId, status, q, page: lastPage }));
      }
      setClamped(true);
    }
  }, [items, total, page, campaignId, status, q, router]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const newestUpdate = useMemo(() => {
    if (!items?.length) return null;
    return items.reduce<string | null>((latest, message) => {
      if (!latest) return message.updated_at;
      return new Date(message.updated_at) > new Date(latest) ? message.updated_at : latest;
    }, null);
  }, [items]);

  const allPending = Boolean(items?.length) && items!.every((item) => item.internal_status === "pending");
  const filtered = Boolean(campaignId || status || q);
  const firstLoad = loading && items === null;

  if (forbidden) {
    return (
      <>
        <PageHeader
          title="سجل الرسائل"
          subtitle="بحث وتصفية في الرسائل التي أُنشئت من الحملات المعتمدة."
        />
        <div className="fd-card">
          <EmptyState
            icon={Lock}
            title="لا تملك صلاحية عرض سجل الرسائل."
            description="تواصل مع مدير النظام إن كنت تحتاج الوصول إلى سجل الرسائل."
            action={
              <Link href="/" className="fd-btn fd-btn-secondary h-11">
                العودة إلى الرئيسية
              </Link>
            }
          />
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="سجل الرسائل"
        subtitle="بحث وتصفية في الرسائل التي أُنشئت من الحملات المعتمدة."
      />

      <HistoryNotice className="mb-4" />

      <MessagesFilterBar
        campaignId={campaignId}
        status={status}
        q={q}
        campaigns={campaigns}
        selectedCampaignName={selectedCampaignName}
        busy={loading}
      />

      <p className="mb-4 min-h-[18px] text-[12px] text-[var(--fd-ink-muted)]">
        {items === null ? (
          "—"
        ) : (
          <>
            الرسائل: {formatNumber(total)}
            {newestUpdate && (
              <>
                {" · "}آخر تحديث في هذه الصفحة{" "}
                <bdi dir="ltr">{formatted(newestUpdate)}</bdi>
              </>
            )}
          </>
        )}
      </p>

      {sessionExpired && (
        <div
          role="alert"
          className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-4 py-3 text-[12px] text-[var(--fd-red-text)]"
        >
          <span>انتهت الجلسة. سجّل الدخول مرة أخرى.</span>
          <Link href="/login?reason=expired" className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]">
            تسجيل الدخول
          </Link>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-4 py-3 text-[12px] text-[var(--fd-red-text)]"
        >
          <span>تعذر تحميل الرسائل. {error}</span>
          <button
            type="button"
            onClick={reload}
            className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
          >
            <RefreshCw size={14} aria-hidden />
            إعادة المحاولة
          </button>
        </div>
      )}

      <section className="fd-card overflow-hidden" aria-labelledby="messages-title">
        <h2 id="messages-title" className="sr-only">
          سجل الرسائل
        </h2>

        {clamped && (
          <p className="border-b border-[var(--fd-line)] px-5 py-2 text-[12px] text-[var(--fd-ink-muted)]">
            عُرضت الصفحة الأخيرة.
          </p>
        )}

        {items === null ? (
          <div className="px-4 py-3" aria-busy={loading}>
            <MessageTable
              messages={[]}
              loading={loading}
              caption="سجل الرسائل. الأحدث أولًا، مع الحملة ورقم الهاتف والمبلغ وحالة آخر محاولة."
              formatted={formatted}
            />
          </div>
        ) : items.length > 0 ? (
          <>
            <MessageTable
              messages={items}
              loading={loading}
              caption="سجل الرسائل. الأحدث أولًا، مع الحملة ورقم الهاتف والمبلغ وحالة آخر محاولة."
              formatted={formatted}
            />
            {allPending && (
              <p className="border-t border-[var(--fd-line)] px-5 py-3 text-[12px] text-[var(--fd-ink-muted)]">
                لم تبدأ معالجة الرسائل بعد. لا شيء أُرسل إلى المزوّد حتى الآن.
              </p>
            )}
          </>
        ) : items ? (
          <EmptyState
            icon={filtered ? FilterX : MessageSquare}
            title={filtered ? "لا توجد رسائل مطابقة" : "لا توجد رسائل بعد"}
            description={
              filtered
                ? "جرّب حالة أخرى أو امسح البحث."
                : "تُنشأ رسالة واحدة لكل مستلم عند اعتماد الحملة، وتظهر هنا بحالة «بانتظار الإرسال»."
            }
            action={
              filtered ? (
                <Link href="/messages" className="fd-btn fd-btn-secondary h-11">
                  مسح عوامل التصفية
                </Link>
              ) : (
                <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
                  عرض الحملات
                </Link>
              )
            }
          />
        ) : null}

        {!firstLoad && !error && total > PAGE_SIZE && (
          <TablePager
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            onPage={(next) =>
              router.push(messagesHref({ campaign_id: campaignId, status, q, page: next }))
            }
            busy={loading}
            itemLabel="رسالة"
          />
        )}
      </section>
    </>
  );
}
