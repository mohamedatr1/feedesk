"use client";

import Link from "next/link";
import { Eye, Plus, Power } from "lucide-react";
import { formatDateTime } from "@/lib/api";
import type { TemplateSummary } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";

export function TemplateVersionList({
  templates,
  isAdmin,
  locale,
  timeZone,
  onActivate,
  activatingId,
}: {
  templates: TemplateSummary[];
  isAdmin: boolean;
  locale?: string | null;
  timeZone?: string | null;
  onActivate: (template: TemplateSummary) => void;
  activatingId: string | null;
}) {
  const groups = new Map<string, TemplateSummary[]>();
  templates.forEach((template) => {
    const rows = groups.get(template.name) ?? [];
    rows.push(template);
    groups.set(template.name, rows);
  });

  return (
    <div className="space-y-4">
      {[...groups.entries()].map(([name, versions]) => {
        const active = versions.find((version) => version.is_active) ?? null;
        const newest = versions[0];
        const editorSource = active ?? newest;
        return (
          <section
            key={name}
            className="fd-card overflow-hidden"
            aria-labelledby={`template-group-${newest?.id ?? name}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--fd-line)] px-5 py-4">
              <div className="min-w-0">
                <h2
                  id={`template-group-${newest?.id ?? name}`}
                  className="truncate text-[15px] font-semibold text-[var(--fd-ink)]"
                >
                  <bdi dir="auto">{name}</bdi>
                </h2>
                <p
                  className={`mt-0.5 text-[11px] ${
                    active ? "text-[var(--fd-ink-muted)]" : "text-[var(--fd-amber-text)]"
                  }`}
                >
                  {active
                    ? `النشط: الإصدار ${active.version}`
                    : "لا يوجد إصدار نشط"}
                </p>
              </div>
              {isAdmin && editorSource && (
                <Link
                  href={`/settings/templates/new?from=${editorSource.id}`}
                  className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                >
                  <Plus size={15} aria-hidden />
                  إصدار جديد
                </Link>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="fd-table min-w-0 lg:min-w-[620px]">
                <caption className="sr-only">
                  إصدارات القالب {name}، الأحدث أولًا، مع حالة التفعيل والمتغيرات غير المعروفة.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">الإصدار</th>
                    <th scope="col">الحالة</th>
                    <th scope="col" className="hidden lg:table-cell">متغيرات غير معروفة</th>
                    <th scope="col" className="hidden xl:table-cell">أنشأه</th>
                    <th scope="col" className="hidden whitespace-nowrap lg:table-cell">تاريخ الإنشاء</th>
                    <th scope="col" className="w-[1%] whitespace-nowrap">
                      <span className="sr-only">الإجراءات</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {versions.map((template) => (
                    <tr
                      key={template.id}
                      className={
                        template.is_active
                          ? "bg-[var(--fd-green-soft)] hover:bg-[var(--fd-green-soft)]"
                          : "hover:bg-[var(--fd-surface-alt)]"
                      }
                    >
                      <th
                        scope="row"
                        className={`bg-transparent text-right text-[13px] font-normal text-[var(--fd-ink)] ${
                          template.is_active ? "bg-transparent" : ""
                        }`}
                      >
                        <span className="tabular-nums">الإصدار {template.version}</span>
                      </th>
                      <td>
                        {template.is_active ? (
                          <StatusPill tone="green">نشط</StatusPill>
                        ) : (
                          <StatusPill tone="neutral">غير نشط</StatusPill>
                        )}
                      </td>
                      <td className="hidden max-w-[260px] lg:table-cell">
                        {template.unknown_variables.length > 0 ? (
                          <span className="text-[12px] text-[var(--fd-amber-text)]">
                            {template.unknown_variables.map((variable, index) => (
                              <span key={variable}>
                                {index > 0 ? "، " : ""}
                                <bdi dir="ltr" lang="en">{`{{${variable}}}`}</bdi>
                              </span>
                            ))}
                          </span>
                        ) : (
                          <span className="text-[var(--fd-ink-subtle)]">—</span>
                        )}
                      </td>
                      <td className="hidden whitespace-nowrap text-[12px] xl:table-cell">
                        <bdi dir="auto">{template.created_by_name ?? "—"}</bdi>
                      </td>
                      <td className="hidden whitespace-nowrap text-[12px] tabular-nums lg:table-cell">
                        <bdi dir="ltr">
                          {formatDateTime(template.created_at, { locale, timeZone })}
                        </bdi>
                      </td>
                      <td>
                        <div className="flex items-center gap-1">
                          <Link
                            href={`/settings/templates/${template.id}`}
                            className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                            aria-label={`عرض القالب ${name} الإصدار ${template.version}`}
                          >
                            <Eye size={15} aria-hidden />
                            عرض
                          </Link>
                          {isAdmin && !template.is_active && (
                            <button
                              type="button"
                              onClick={() => onActivate(template)}
                              disabled={activatingId === template.id}
                              className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
                              aria-label={`تفعيل القالب ${name} الإصدار ${template.version}`}
                            >
                              <Power size={15} aria-hidden />
                              تفعيل
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}
    </div>
  );
}
