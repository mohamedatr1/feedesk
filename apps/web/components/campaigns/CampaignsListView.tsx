"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  BarChart3,
  ClipboardCheck,
  Eye,
  FileSpreadsheet,
  Megaphone,
  Plus,
  RefreshCw,
} from "lucide-react";
import {
  ApiError,
  api,
  formatDateTime,
  formatNumber,
  type CampaignStatus,
  type CampaignSummary,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { CurrencyTotals } from "@/components/imports/CurrencyTotals";
import { TablePager } from "@/components/imports/TablePager";
import { CampaignStatusPill } from "@/components/campaigns/CampaignStatusPill";
import { CampaignFilterTabs } from "@/components/campaigns/CampaignFilterTabs";
import { NoSendNotice } from "@/components/campaigns/NoSendNotice";
import { hasPermission, usePermissions } from "@/components/campaigns/permissions";
import {
  CAMPAIGN_STATUSES,
  campaignStatusMeaning,
  isProcessingCampaignStatus,
} from "@/components/campaigns/campaign-format";

const PAGE_SIZE = 20;
type CountMap = Record<string, number | null>;

function statusSecondLine(
  campaign: CampaignSummary,
  formatted: (value: string | null) => string,
): string {
  if (campaign.status === "draft") {
    return campaign.updated_at
      ? `آخر معاينة ${formatted(campaign.updated_at)}`
      : "لم تُراجع بعد";
  }
  if (campaign.status === "awaiting_approval") {
    return `أُرسلت للاعتماد ${formatted(campaign.submitted_at)}`;
  }
  if (campaign.status === "approved") {
    return `اعتُمدت ${formatted(campaign.approved_at)}`;
  }
  if (campaign.status === "cancelled") {
    return `أُلغيت ${formatted(campaign.cancelled_at)}`;
  }
  if (isProcessingCampaignStatus(campaign.status)) {
    return campaignStatusMeaning(campaign.status);
  }
  return "";
}

export function CampaignsListView({ status }: { status: CampaignStatus | "" }) {
  return (
    <Protected active="/campaigns">
      <CampaignsListContent status={status} />
    </Protected>
  );
}

function CampaignsListContent({ status }: { status: CampaignStatus | "" }) {
  const { user, settings } = useSession();
  const permissions = usePermissions();
  const canCreate = hasPermission(permissions, user.role, "campaigns.create");
  const canApprove = hasPermission(permissions, user.role, "campaigns.approve");

  const [items, setItems] = useState<CampaignSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [counts, setCounts] = useState<CountMap>({
    "": null,
    draft: null,
    awaiting_approval: null,
    approved: null,
    cancelled: null,
  });
  const [countsLoading, setCountsLoading] = useState(true);
  const [lastCreatedAt, setLastCreatedAt] = useState<string | null>(null);

  const formatted = useCallback(
    (value: string | null) =>
      value
        ? formatDateTime(value, { locale: settings?.locale, timeZone: settings?.timezone })
        : "—",
    [settings?.locale, settings?.timezone],
  );

  useEffect(() => {
    setPage(1);
  }, [status]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    api
      .listCampaigns({ page, page_size: PAGE_SIZE, status })
      .then((data) => {
        if (!mounted) return;
        setItems(data.items ?? []);
        setTotal(data.total ?? 0);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 401) {
          setError("انتهت الجلسة. أعد تسجيل الدخول للمتابعة.");
        } else if (err instanceof ApiError && err.status === 403) {
          setError("لا تملك صلاحية عرض الحملات.");
        } else {
          setError(err instanceof ApiError ? err.messageAr : "تعذر تحميل الحملات.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [page, status, reloadKey]);

  useEffect(() => {
    let mounted = true;
    setCountsLoading(true);

    const probes: Array<Promise<{ key: string; total: number; latest: string | null }>> = [
      { key: "", status: "" },
      ...CAMPAIGN_STATUSES.map((value) => ({ key: value, status: value })),
    ].map(({ key, status: probeStatus }) =>
      api
        .listCampaigns({ page: 1, page_size: 1, status: probeStatus as CampaignStatus | "" })
        .then((data) => ({
          key,
          total: data.total ?? 0,
          latest: data.items?.[0]?.created_at ?? null,
        })),
    );

    Promise.allSettled(probes).then((results) => {
      if (!mounted) return;
      const next: CountMap = {};
      let latest: string | null = null;
      results.forEach((result, index) => {
        const key = probes.length > index ? ["", ...CAMPAIGN_STATUSES][index] : "";
        next[key] = result.status === "fulfilled" ? result.value.total : null;
        if (result.status === "fulfilled" && key === "" && result.value.latest) {
          latest = result.value.latest;
        }
      });
      setCounts(next);
      setLastCreatedAt(latest);
      setCountsLoading(false);
    });

    return () => {
      mounted = false;
    };
  }, [reloadKey]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasAnyCount = Object.values(counts).some((value) => value != null);
  const showSummary = !countsLoading && hasAnyCount && (counts[""] ?? 0) > 0;

  return (
    <>
      <PageHeader
        title="الحملات"
        subtitle="إعداد حملات التذكير من الكشوف المؤكدة، معاينتها، ثم اعتمادها."
        action={
          canCreate ? (
            <Link href="/campaigns/new" className="fd-btn fd-btn-primary h-11">
              <Plus size={16} aria-hidden />
              حملة جديدة
            </Link>
          ) : undefined
        }
      />

      <NoSendNotice className="mb-4" />

      <p className="mb-4 min-h-[18px] text-[12px] text-[var(--fd-ink-muted)]">
        {countsLoading ? (
          "— · — · —"
        ) : showSummary ? (
          <>
            الحملات: {formatNumber(counts[""] ?? 0)}
            {(counts.awaiting_approval ?? 0) > 0 &&
              ` · بانتظار الاعتماد: ${formatNumber(counts.awaiting_approval ?? 0)}`}
            {lastCreatedAt && (
              <>
                {" · آخر حملة "}
                <bdi dir="ltr">{formatted(lastCreatedAt)}</bdi>
              </>
            )}
          </>
        ) : null}
      </p>

      <div className="mb-4">
        <CampaignFilterTabs current={status} counts={counts} />
      </div>

      {error && (
        <div
          role="alert"
          className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-4 py-3 text-[12px] text-[var(--fd-red-text)]"
        >
          <span>تعذر تحميل الحملات. {error}</span>
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

      <section className="fd-card overflow-hidden" aria-labelledby="campaigns-title">
        <h2 id="campaigns-title" className="sr-only">
          قائمة الحملات
        </h2>

        <div className="overflow-x-auto">
          <table className="fd-table min-w-0 xl:min-w-[820px]" aria-busy={loading}>
            <caption className="sr-only">
              قائمة الحملات. الأحدث أولًا، مع عدد المستلمين والإجماليات لكل عملة.
            </caption>
            <thead>
              <tr>
                <th scope="col">الحملة</th>
                <th scope="col" className="hidden xl:table-cell">المصدر</th>
                <th scope="col" className="hidden md:table-cell">المستلمون</th>
                <th scope="col" className="hidden sm:table-cell">الإجماليات</th>
                <th scope="col" className="hidden sm:table-cell">الحالة</th>
                <th scope="col" className="hidden xl:table-cell">أنشأها</th>
                <th scope="col" className="hidden lg:table-cell">اعتمادها</th>
                <th scope="col" className="w-[1%] whitespace-nowrap">
                  <span className="sr-only">الإجراءات</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {loading &&
                Array.from({ length: 5 }).map((_, index) => (
                  <tr key={`skeleton-${index}`}>
                    <td colSpan={8}>
                      <div className="fd-skeleton h-8 w-full" />
                    </td>
                  </tr>
                ))}

              {!loading &&
                items.map((campaign) => {
                  const action =
                    campaign.status === "draft"
                      ? {
                          label: "متابعة الإعداد",
                          icon: ClipboardCheck,
                          primary: false,
                          href: `/campaigns/${campaign.id}`,
                        }
                      : campaign.status === "awaiting_approval"
                        ? {
                            label: "مراجعة واعتماد",
                            icon: ClipboardCheck,
                            primary: canApprove,
                            href: `/campaigns/${campaign.id}`,
                          }
                        : isProcessingCampaignStatus(campaign.status)
                          ? {
                              label: "النتائج",
                              icon: BarChart3,
                              primary: false,
                              href: `/campaigns/${campaign.id}/results`,
                            }
                          : {
                              label: "عرض",
                              icon: Eye,
                              primary: false,
                              href: `/campaigns/${campaign.id}`,
                            };

                  const ActionIcon = action.icon;

                  return (
                    <tr
                      key={campaign.id}
                      className="min-h-[64px] hover:bg-[var(--fd-surface-alt)] focus-within:bg-[var(--fd-brand-soft)]/40"
                    >
                      <th
                        scope="row"
                        className="min-w-[96px] max-w-[260px] bg-transparent text-right align-top text-[13px] font-normal text-[var(--fd-ink)] sm:min-w-[220px]"
                      >
                        <Link
                          href={`/campaigns/${campaign.id}`}
                          className="block truncate font-medium text-[var(--fd-ink)] hover:text-[var(--fd-brand)] hover:underline"
                        >
                          <bdi dir="auto">{campaign.name}</bdi>
                        </Link>
                        <p className="mt-0.5 truncate text-[11px] text-[var(--fd-ink-subtle)]">
                          القالب: <bdi dir="auto">{campaign.template_name ?? "—"}</bdi>
                          {campaign.template_version != null
                            ? ` · إ${campaign.template_version}`
                            : ""}
                        </p>
                        <p className="mt-0.5 truncate text-[10px] text-[var(--fd-ink-subtle)] xl:hidden">
                          <bdi dir="auto">{campaign.source_filename ?? "—"}</bdi>
                          {campaign.created_by_name ? ` · ${campaign.created_by_name}` : ""}
                          {` · ${formatted(campaign.created_at)}`}
                        </p>
                        <p className="mt-1.5 sm:hidden">
                          <CampaignStatusPill status={campaign.status} />
                        </p>
                      </th>
                      <td className="hidden max-w-[150px] align-top xl:table-cell">
                        <bdi dir="auto" className="block truncate text-[12px]">
                          {campaign.source_filename ?? "—"}
                        </bdi>
                        <p className="mt-0.5 whitespace-nowrap text-[10px] text-[var(--fd-ink-subtle)]">
                          أُنشئت <bdi dir="ltr">{formatted(campaign.created_at)}</bdi>
                        </p>
                      </td>
                      <td className="hidden align-top md:table-cell">
                        <p className="text-[15px] font-semibold tabular-nums">
                          {formatNumber(campaign.recipient_count)}
                        </p>
                        {campaign.excluded_count > 0 && (
                          <p className="text-[11px] text-[var(--fd-ink-subtle)]">
                            مستثنى {formatNumber(campaign.excluded_count)}
                          </p>
                        )}
                      </td>
                      <td className="hidden align-top sm:table-cell">
                        <CurrencyTotals totals={campaign.totals_by_currency} />
                        {Object.keys(campaign.totals_by_currency ?? {}).length === 0 && (
                          <span className="text-[12px] text-[var(--fd-ink-subtle)]">—</span>
                        )}
                      </td>
                      <td className="hidden align-top sm:table-cell">
                        <CampaignStatusPill status={campaign.status} />
                        <p className="mt-1 break-words text-[10px] leading-5 text-[var(--fd-ink-subtle)]">
                          {statusSecondLine(campaign, formatted)}
                        </p>
                      </td>
                      <td className="hidden whitespace-nowrap align-top text-[12px] xl:table-cell">
                        <bdi dir="auto">{campaign.created_by_name ?? "—"}</bdi>
                        <p className="tabular-nums text-[10px] text-[var(--fd-ink-subtle)]">
                          <bdi dir="ltr">{formatted(campaign.created_at)}</bdi>
                        </p>
                      </td>
                      <td className="hidden whitespace-nowrap align-top text-[12px] lg:table-cell">
                        {campaign.approved_at ? (
                          <>
                            <bdi dir="auto">{campaign.approved_by_name ?? "—"}</bdi>
                            <p className="tabular-nums text-[10px] text-[var(--fd-ink-subtle)]">
                              <bdi dir="ltr">{formatted(campaign.approved_at)}</bdi>
                            </p>
                          </>
                        ) : (
                          <span className="text-[var(--fd-ink-subtle)]">—</span>
                        )}
                      </td>
                      <td className="align-top">
                        <Link
                          href={action.href}
                          className={`fd-btn h-11 px-3 text-[12px] ${
                            action.primary ? "fd-btn-primary" : "fd-btn-secondary"
                          }`}
                          aria-label={`${action.label} حملة ${campaign.name}`}
                        >
                          <ActionIcon size={15} aria-hidden />
                          {action.label}
                        </Link>
                      </td>
                    </tr>
                  );
                })}

              {!loading && items.length === 0 && !error && (
                <tr>
                  <td colSpan={8}>
                    <EmptyState
                      icon={Megaphone}
                      title={
                        status
                          ? "لا توجد حملات بهذه الحالة"
                          : "لا توجد حملات بعد"
                      }
                      description={
                        status
                          ? "جرّب حالة أخرى."
                          : "أنشئ حملة من كشف أقساط مؤكد لمعاينة المستلمين والمبالغ قبل الاعتماد."
                      }
                      action={
                        status ? (
                          <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
                            عرض كل الحملات
                          </Link>
                        ) : canCreate ? (
                          <div className="flex flex-col items-center gap-2">
                            <Link
                              href="/campaigns/new"
                              className="fd-btn fd-btn-secondary h-11"
                            >
                              حملة جديدة
                            </Link>
                            <span className="text-[11px] text-[var(--fd-ink-subtle)]">
                              تحتاج كشفًا مؤكدًا أولًا.{" "}
                              <Link
                                href="/statements"
                                className="font-medium text-[var(--fd-brand)] hover:underline"
                              >
                                عرض الكشوف
                              </Link>
                            </span>
                          </div>
                        ) : (
                          <Link href="/statements" className="fd-btn fd-btn-secondary h-11">
                            عرض الكشوف
                          </Link>
                        )
                      }
                    />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {!loading && !error && total > PAGE_SIZE && (
          <TablePager
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            onPage={(next) => setPage(Math.min(totalPages, Math.max(1, next)))}
            itemLabel="حملة"
          />
        )}
      </section>
    </>
  );
}
