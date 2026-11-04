"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  FileSearch,
  Info,
  Lock,
  RefreshCw,
  Send,
  Upload,
  Users,
  Wallet,
} from "lucide-react";
import {
  ApiError,
  api,
  formatDateTime,
  formatNumber,
  type DashboardData,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { messagesHref } from "@/components/messages/message-format";
import { ActionQueue } from "@/components/dashboard/ActionQueue";
import { ActivityTable } from "@/components/dashboard/ActivityTable";
import { KpiCard, type KpiCurrencyTotal, type KpiCurrencyTrend } from "@/components/dashboard/KpiCard";
import { ProviderCard } from "@/components/dashboard/ProviderCard";
import { QuickMetrics, type QuickMetric } from "@/components/dashboard/QuickMetrics";
import {
  countPhrase,
  currencyDelta,
  currencyDisplay,
  currencyEntries,
  currencySeries,
} from "@/components/dashboard/dashboard-format";

const ACTIVITY_LIMIT = 5;
const TREND_DAYS = 30;

export function DashboardView() {
  const { user, settings } = useSession();
  const isAdmin = user.role === "admin";

  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);

  const formatted = useCallback(
    (value: string | null) =>
      value
        ? formatDateTime(value, { locale: settings?.locale, timeZone: settings?.timezone })
        : "—",
    [settings?.locale, settings?.timezone],
  );

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    setSessionExpired(false);
    setForbidden(false);

    api
      .getDashboard({ activity_limit: ACTIVITY_LIMIT, trend_days: TREND_DAYS })
      .then((result) => {
        if (!mounted) return;
        setData(result);
        if (reloadKey > 0) setRefreshedAt(formatDateTime(new Date().toISOString()));
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 401) {
          setSessionExpired(true);
        } else if (err instanceof ApiError && err.status === 403) {
          setForbidden(true);
        } else {
          setError(err instanceof ApiError ? err.messageAr : "تعذر تحميل لوحة المعلومات.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [reloadKey]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  if (forbidden) {
    return (
      <>
        <PageHeader
          title="الرئيسية"
          subtitle="نظرة عامة على الوضع المالي وحالة التذكيرات."
        />
        <div className="fd-card">
          <EmptyState
            icon={Lock}
            title="لا تملك صلاحية عرض لوحة المعلومات."
            description="تواصل مع مدير النظام إن كنت تحتاج الوصول إلى هذه الأرقام."
          />
        </div>
      </>
    );
  }

  const counts = data?.counts ?? null;
  const totals = currencyEntries(data?.totals_by_currency);

  const trends = data?.trends ?? null;
  const trendsAvailable = trends?.available === true;
  const basisDays = trends?.basis_days ?? 0;

  /**
   * Per-currency trend only. A currency without a finite `pct` gets no delta,
   * and nothing is aggregated across currencies.
   */
  function trendForCurrency(currency: string): KpiCurrencyTrend | null {
    if (!trends || !trendsAvailable) return null;
    const pct = currencyDelta(trends.deltas, currency);
    if (pct === null) return null;
    return { pct, points: currencySeries(trends.series, currency) };
  }

  const currencyTotals: KpiCurrencyTotal[] = totals.map(([currency, amount]) => ({
    currency,
    amount,
    label: currencyDisplay(currency, settings?.default_currency, settings?.currency_symbol),
    trend: trendForCurrency(currency),
  }));

  const totalsHint =
    totals.length === 0
      ? "لا توجد أرصدة مستحقة مؤكدة."
      : (counts?.outstanding_records ?? 0) > 0
        ? `عبر ${countPhrase(counts?.outstanding_records ?? 0, "records")}`
        : "من الكشوف المؤكدة.";

  const guardiansHint =
    (counts?.outstanding_guardians ?? 0) > 0
      ? "لديهم رصيد متبقٍّ في الكشوف المؤكدة."
      : "لا أولياء أمور عليهم أرصدة مستحقة.";

  const reviewHint =
    (counts?.imports_awaiting_review ?? 0) > 0
      ? (counts?.imports_total ?? 0) > 0
        ? `من أصل ${countPhrase(counts?.imports_total ?? 0, "imports")}`
        : "بانتظار قرارك قبل تأكيد الاستيراد."
      : "لا كشوف بانتظار المراجعة.";

  const approvalHint =
    (counts?.campaigns_awaiting_approval ?? 0) > 0
      ? (counts?.campaigns_total ?? 0) > 0
        ? `من أصل ${countPhrase(counts?.campaigns_total ?? 0, "campaigns")}`
        : "بانتظار اعتماد مدير النظام."
      : "لا حملات بانتظار الاعتماد.";

  const quickItems: QuickMetric[] = counts
    ? [
        {
          label: "كشوف قيد المعالجة",
          value: counts.imports_processing,
          href: "/statements",
        },
        {
          label: "حملات نشطة",
          value: counts.campaigns_active,
          href: "/campaigns",
        },
        {
          label: "رسائل فشلت مؤخرًا",
          value: counts.messages_failed_recent,
          href: messagesHref({ status: "failed" }),
          tone: counts.messages_failed_recent > 0 ? "red" : "neutral",
        },
        {
          label: "نتائج غير معروفة مؤخرًا",
          value: counts.messages_unknown_recent,
          href: messagesHref({ status: "unknown" }),
          tone: counts.messages_unknown_recent > 0 ? "amber" : "neutral",
        },
      ]
    : [];

  return (
    <>
      <PageHeader
        title="الرئيسية"
        subtitle="نظرة عامة على الوضع المالي وحالة التذكيرات."
        action={
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={reload}
              disabled={loading}
              className="fd-btn fd-btn-secondary h-11"
            >
              <RefreshCw size={15} className={loading ? "animate-spin" : ""} aria-hidden />
              تحديث
            </button>
            <Link href="/statements/upload" className="fd-btn fd-btn-primary h-11">
              <Upload size={16} aria-hidden />
              رفع كشوف جديدة
            </Link>
          </div>
        }
      />

      <p role="status" className="mb-4 min-h-[18px] text-[12px] text-[var(--fd-ink-muted)]">
        {loading
          ? data
            ? "جارٍ تحديث بيانات اللوحة…"
            : "جارٍ تحميل لوحة المعلومات…"
          : data
            ? (
                <>
                  بيانات حتى <bdi dir="ltr">{data.as_of_date}</bdi>
                  {" · "}آخر توليد <bdi dir="ltr">{formatted(data.generated_at)}</bdi>
                  {refreshedAt && (
                    <>
                      {" · "}حُدِّثت الشاشة <bdi dir="ltr">{refreshedAt}</bdi>
                    </>
                  )}
                </>
              )
            : "—"}
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
          <span>تعذر تحميل لوحة المعلومات. {error}</span>
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

      {data ? (
        <div aria-busy={loading}>
          <section aria-labelledby="dashboard-kpis-title">
            <h2 id="dashboard-kpis-title" className="sr-only">
              ملخص الأرقام
            </h2>
            <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
              <KpiCard
                className="col-span-2 xl:col-span-1"
                label="إجمالي المستحقات"
                icon={Wallet}
                currencyTotals={currencyTotals}
                hint={totalsHint}
                basisDays={basisDays}
              />
              <KpiCard
                label="أولياء الأمور المستحقون"
                icon={Users}
                value={counts ? formatNumber(counts.outstanding_guardians) : "—"}
                hint={guardiansHint}
              />
              <KpiCard
                label="كشوف بانتظار المراجعة"
                icon={FileSearch}
                value={counts ? formatNumber(counts.imports_awaiting_review) : "—"}
                hint={reviewHint}
              />
              <KpiCard
                label="حملات بانتظار الاعتماد"
                icon={Send}
                value={counts ? formatNumber(counts.campaigns_awaiting_approval) : "—"}
                hint={approvalHint}
              />
            </div>

            {!trendsAvailable && (
              <p className="mt-2 flex items-center gap-1.5 px-1 text-[12px] text-[var(--fd-ink-muted)]">
                <Info size={14} aria-hidden className="shrink-0" />
                تظهر الاتجاهات بعد توفر لقطات كافية.
              </p>
            )}
          </section>

          {quickItems.length > 0 && (
            <div className="mt-4">
              <QuickMetrics items={quickItems} />
            </div>
          )}

          <div className="mt-5 grid gap-5 lg:grid-cols-[1.5fr_1fr]">
            <ActionQueue items={data.action_queue ?? []} />
            <ProviderCard isAdmin={isAdmin} />
          </div>

          <ActivityTable
            items={data.recent_activity ?? []}
            isAdmin={isAdmin}
            formatted={formatted}
          />
        </div>
      ) : loading ? (
        <div aria-hidden>
          <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className={`fd-skeleton h-[150px] ${index === 0 ? "col-span-2 xl:col-span-1" : ""}`}
              />
            ))}
          </div>
          <div className="fd-skeleton mt-4 h-[76px]" />
          <div className="mt-5 grid gap-5 lg:grid-cols-[1.5fr_1fr]">
            <div className="fd-skeleton h-[300px]" />
            <div className="fd-skeleton h-[240px]" />
          </div>
          <div className="fd-skeleton mt-5 h-[260px]" />
        </div>
      ) : null}
    </>
  );
}
