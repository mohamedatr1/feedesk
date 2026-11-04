import { formatDecimalString } from "@/lib/api";
import type { ExcludedRecord } from "@/lib/api";
import { exclusionHint } from "@/components/campaigns/campaign-format";

export function ExcludedTable({
  excluded,
  campaignName,
  frozen = false,
}: {
  excluded: ExcludedRecord[];
  campaignName: string;
  frozen?: boolean;
}) {
  if (!excluded || excluded.length === 0) return null;

  return (
    <section
      id="excluded-panel"
      className="fd-card overflow-hidden"
      aria-labelledby="excluded-title"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--fd-line)] px-5 py-4">
        <h2 id="excluded-title" className="text-sm font-semibold text-[var(--fd-ink)]">
          المستثناة ({excluded.length})
        </h2>
        <p className="text-[11px] text-[var(--fd-ink-subtle)]">
          {frozen
            ? "كما كانت وقت الاعتماد."
            : "هذه السجلات لم تدخل الحملة. الأسباب من بيانات الكشف المؤكد."}
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="fd-table min-w-0 lg:min-w-[640px]">
          <caption className="sr-only">
            السجلات المستثناة من حملة {campaignName} مع سبب الاستثناء.
          </caption>
          <thead>
            <tr>
              <th scope="col">ولي الأمر</th>
              <th scope="col" className="hidden lg:table-cell">الهاتف</th>
              <th scope="col">المبلغ</th>
              <th scope="col" className="hidden md:table-cell">العملة</th>
              <th scope="col">سبب الاستثناء</th>
            </tr>
          </thead>
          <tbody>
            {excluded.map((record, index) => {
              // Detail responses omit full phones; preview responses keep both.
              // Always prefer the masked value so preview data never leaks here.
              const displayPhone = record.phone_masked || record.phone;
              return (
                <tr
                  key={record.key ?? `${record.guardian_id}-${record.currency ?? index}`}
                  className="hover:bg-[var(--fd-surface-alt)]"
                >
                  <th
                    scope="row"
                    className="min-w-[110px] bg-transparent text-right align-top text-[13px] font-normal text-[var(--fd-ink)] sm:min-w-[160px]"
                  >
                    <bdi dir="auto" className="font-medium">
                      {record.guardian_name || "—"}
                    </bdi>
                    <p className="mt-0.5 text-[11px] text-[var(--fd-ink-subtle)] lg:hidden">
                      {displayPhone ? (
                        <bdi dir="ltr">{displayPhone}</bdi>
                      ) : (
                        "لا يوجد رقم هاتف"
                      )}
                    </p>
                  </th>
                  <td className="align-top whitespace-nowrap hidden lg:table-cell">
                    {displayPhone ? (
                      <bdi dir="ltr">{displayPhone}</bdi>
                    ) : (
                      <span className="text-[var(--fd-ink-subtle)]">—</span>
                    )}
                  </td>
                  <td className="align-top whitespace-nowrap tabular-nums">
                    <bdi dir="ltr">
                      {formatDecimalString(record.amount)}
                      {record.currency ? (
                        <span className="ms-1 text-[11px] text-[var(--fd-ink-subtle)] md:hidden">
                          {record.currency}
                        </span>
                      ) : null}
                    </bdi>
                  </td>
                  <td className="align-top hidden md:table-cell">
                    {record.currency ? (
                      <bdi dir="ltr" lang="en" className="text-[11px] text-[var(--fd-ink-muted)]">
                        {record.currency}
                      </bdi>
                    ) : (
                      <span className="text-[var(--fd-ink-subtle)]">—</span>
                    )}
                  </td>
                  <td className="align-top">
                    <ul className="space-y-1">
                      {record.reasons.map((reason, reasonIndex) => {
                        const hint = exclusionHint(reason.code);
                        return (
                          <li key={`${reason.code}-${reasonIndex}`} className="text-[12px] leading-5">
                            <span className="text-[var(--fd-ink)]">{reason.message_ar}</span>
                            {hint && (
                              <span className="block text-[11px] text-[var(--fd-ink-subtle)]">
                                {hint}
                              </span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
