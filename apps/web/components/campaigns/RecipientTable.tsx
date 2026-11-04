"use client";

import { useMemo, useState } from "react";
import { Eye, Loader2, TriangleAlert, Users } from "lucide-react";
import { formatDecimalString } from "@/lib/api";
import type { CampaignRecipient } from "@/lib/api";
import { EmptyState } from "@/components/EmptyState";
import { StatusPill } from "@/components/StatusPill";
import { TablePager } from "@/components/imports/TablePager";

const PAGE_SIZE = 50;

/** The detail response only carries a student count, so label the count only. */
function studentCountLabel(count: number): string {
  if (count <= 0) return "—";
  if (count === 1) return "طالب واحد";
  if (count === 2) return "طالبان";
  const formatted = new Intl.NumberFormat("ar-EG").format(count);
  return `${formatted} طلاب`;
}

export function RecipientTable({
  recipients,
  campaignName,
  frozen = false,
  showExcludedAction = false,
  onShowExcluded,
  canPreview = false,
  previewLoadingKey = null,
  onPreview,
}: {
  recipients: CampaignRecipient[];
  campaignName: string;
  frozen?: boolean;
  showExcludedAction?: boolean;
  onShowExcluded?: () => void;
  canPreview?: boolean;
  previewLoadingKey?: string | null;
  onPreview?: (recipient: CampaignRecipient) => void;
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const word = query.trim().toLowerCase();
    if (!word) return recipients;
    return recipients.filter(
      (recipient) =>
        recipient.guardian_name.toLowerCase().includes(word) ||
        (recipient.phone_masked || "").toLowerCase().includes(word),
    );
  }, [recipients, query]);

  const paginated = recipients.length > 100;
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const visible = paginated
    ? filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE)
    : filtered;

  return (
    <section className="fd-card overflow-hidden" aria-labelledby="recipients-title">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--fd-line)] px-5 py-4">
        <div>
          <h2 id="recipients-title" className="text-sm font-semibold text-[var(--fd-ink)]">
            المستلمون ({recipients.length})
          </h2>
          {frozen && (
            <p className="mt-0.5 text-[11px] text-[var(--fd-ink-subtle)]">
              بيانات مثبّتة وقت الاعتماد. لا تتغير بتغيّر الكشف أو أولياء الأمور.
            </p>
          )}
        </div>
        <div className="w-full max-w-[280px]">
          <label htmlFor="recipient-search" className="sr-only">
            ابحث باسم ولي الأمر أو رقم الهاتف
          </label>
          <input
            id="recipient-search"
            type="search"
            className="fd-input h-11"
            placeholder="ابحث باسم ولي الأمر أو رقم الهاتف"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      {recipients.length === 0 ? (
        <EmptyState
          icon={Users}
          title="لا يوجد مستلم مؤهل"
          description="كل السجلات في هذا الكشف استُثنيت. راجع أسباب الاستثناء أدناه."
          action={
            showExcludedAction && onShowExcluded ? (
              <button
                type="button"
                className="fd-btn fd-btn-secondary h-11"
                onClick={onShowExcluded}
              >
                عرض المستثناة
              </button>
            ) : undefined
          }
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="fd-table min-w-0 lg:min-w-[660px]">
            <caption className="sr-only">
              مستلمو حملة {campaignName}، مع المبلغ والعملة وحالة التحقق.
            </caption>
            <thead>
              <tr>
                <th scope="col">ولي الأمر</th>
                <th scope="col" className="hidden md:table-cell">الهاتف</th>
                <th scope="col" className="hidden lg:table-cell">الطلاب</th>
                <th scope="col" className="hidden lg:table-cell">الفصول</th>
                <th scope="col">المبلغ</th>
                <th scope="col" className="hidden md:table-cell">العملة</th>
                <th scope="col">الحالة</th>
                {canPreview && (
                  <th scope="col" className="w-[1%] whitespace-nowrap">
                    <span className="sr-only">الإجراءات</span>
                  </th>
                )}
              </tr>
            </thead>
            <tbody>
              {visible.map((recipient) => {
                const warningCount = recipient.warnings.length;
                return (
                  <tr
                    key={recipient.key}
                    className={`min-h-[64px] hover:bg-[var(--fd-surface-alt)] ${
                      recipient.validation_status === "warning"
                        ? "border-s-[3px] border-s-[var(--fd-amber)]"
                        : ""
                    }`}
                  >
                    <th
                      scope="row"
                      className="min-w-[120px] bg-transparent text-right align-top text-[13px] font-normal text-[var(--fd-ink)] sm:min-w-[170px]"
                    >
                      <bdi dir="auto" className="font-medium">
                        {recipient.guardian_name}
                      </bdi>
                      <p className="mt-0.5 text-[11px] text-[var(--fd-ink-subtle)]">
                        {recipient.fee_balance_ids.length} أرصدة ·{" "}
                        <bdi dir="ltr">{recipient.phone_masked}</bdi>
                      </p>
                    </th>
                    <td className="hidden align-top whitespace-nowrap md:table-cell">
                      <bdi dir="ltr">{recipient.phone_masked}</bdi>
                    </td>
                    <td className="hidden max-w-[190px] truncate align-top text-[12px] lg:table-cell">
                      <bdi>
                        {studentCountLabel(
                          recipient.student_count ?? recipient.student_names.length,
                        )}
                      </bdi>
                    </td>
                    <td className="hidden max-w-[150px] truncate align-top text-[12px] lg:table-cell">
                      {recipient.fee_periods.length > 0
                        ? recipient.fee_periods.join("، ")
                        : "—"}
                    </td>
                    <td className="whitespace-nowrap align-top tabular-nums">
                      <bdi dir="ltr">
                        {formatDecimalString(recipient.amount)}
                        <span className="ms-1 text-[11px] text-[var(--fd-ink-subtle)] md:hidden">
                          {recipient.currency}
                        </span>
                      </bdi>
                    </td>
                    <td className="hidden align-top md:table-cell">
                      <bdi dir="ltr" lang="en" className="text-[11px] text-[var(--fd-ink-muted)]">
                        {recipient.currency}
                      </bdi>
                    </td>
                    <td className="align-top">
                      {recipient.validation_status === "warning" ? (
                        <StatusPill tone="amber">
                          <span className="inline-flex items-center gap-1">
                            <TriangleAlert size={12} aria-hidden />
                            تحذير {warningCount > 0 ? `(${warningCount})` : ""}
                          </span>
                        </StatusPill>
                      ) : (
                        <StatusPill tone="green">صالح</StatusPill>
                      )}
                    </td>
                    {canPreview && onPreview && (
                      <td className="align-top">
                        <button
                          type="button"
                          className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                          onClick={() => onPreview(recipient)}
                          aria-label={`معاينة رسالة ${recipient.guardian_name}`}
                          aria-busy={previewLoadingKey === recipient.key}
                          disabled={previewLoadingKey === recipient.key}
                        >
                          {previewLoadingKey === recipient.key ? (
                            <>
                              <Loader2 size={15} className="animate-spin" aria-hidden />
                              جارٍ التحميل…
                            </>
                          ) : (
                            <>
                              <Eye size={15} aria-hidden />
                              <span className="hidden sm:inline">معاينة الرسالة</span>
                            </>
                          )}
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>

          {query && filtered.length === 0 && (
            <p className="px-5 py-6 text-center text-[12px] text-[var(--fd-ink-muted)]">
              لا يوجد مستلم يطابق البحث.
            </p>
          )}
        </div>
      )}

      {paginated && filtered.length > 0 && (
        <TablePager
          page={safePage}
          pageSize={PAGE_SIZE}
          total={filtered.length}
          onPage={setPage}
          itemLabel="مستلم"
        />
      )}
    </section>
  );
}
