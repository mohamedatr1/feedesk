"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  BookText,
  ChevronLeft,
  Power,
  RefreshCw,
  TriangleAlert,
} from "lucide-react";
import {
  ApiError,
  api,
  formatDateTime,
  type TemplateDetail,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { StatusPill } from "@/components/StatusPill";
import { NoSendNotice } from "@/components/campaigns/NoSendNotice";
import { TemplateBody } from "@/components/templates/TemplateBody";
import { ActivateVersionDialog } from "@/components/templates/ActivateVersionDialog";
import { hasPermission, usePermissions } from "@/components/campaigns/permissions";

export function TemplateVersionDetailView({ templateId }: { templateId: string }) {
  return (
    <Protected active="/settings">
      <TemplateVersionDetailContent templateId={templateId} />
    </Protected>
  );
}

function TemplateVersionDetailContent({ templateId }: { templateId: string }) {
  const { user, settings } = useSession();
  const permissions = usePermissions();
  const canView = hasPermission(permissions, user.role, "templates.view");
  const canManage = hasPermission(permissions, user.role, "templates.manage");

  const [template, setTemplate] = useState<TemplateDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const noticeRef = useRef<HTMLDivElement>(null);

  const [activateOpen, setActivateOpen] = useState(false);
  const [activating, setActivating] = useState(false);
  const [activateError, setActivateError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    setNotFound(false);
    setForbidden(false);

    api
      .getTemplate(templateId)
      .then((data) => {
        if (mounted) setTemplate(data);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        } else if (err instanceof ApiError && err.status === 403) {
          setForbidden(true);
        } else {
          setError(err instanceof ApiError ? err.messageAr : "تعذر تحميل القالب.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [templateId, reloadKey]);

  useEffect(() => {
    if (notice) noticeRef.current?.focus();
  }, [notice]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  async function activate() {
    if (!template) return;
    setActivating(true);
    setActivateError(null);
    try {
      const updated = await api.activateTemplate(template.id);
      setTemplate(updated);
      setActivateOpen(false);
      setNotice(`فُعِّل الإصدار ${updated.version}.`);
    } catch (err) {
      setActivateError(
        err instanceof ApiError ? err.messageAr : "تعذر تفعيل الإصدار. أعد المحاولة.",
      );
    } finally {
      setActivating(false);
    }
  }

  if (!canView || forbidden) {
    return (
      <>
        <div className="fd-card">
          <EmptyState
            icon={BookText}
            title="لا تملك صلاحية عرض هذا القالب"
            description="عرض القوالب متاح للموظفين الإداريين. تواصل مع مدير النظام."
            action={
              <Link href="/settings/templates" className="fd-btn fd-btn-secondary h-11">
                العودة إلى القوالب
              </Link>
            }
          />
        </div>
      </>
    );
  }

  if (notFound) {
    return (
      <>
        <div className="fd-card">
          <EmptyState
            icon={BookText}
            title="لم نجد هذا الإصدار"
            description="قد يكون الرابط قديمًا أو أن الإصدار غير متاح."
            action={
              <Link href="/settings/templates" className="fd-btn fd-btn-secondary h-11">
                العودة إلى القوالب
              </Link>
            }
          />
        </div>
      </>
    );
  }

  if (loading && !template) {
    return (
      <>
        <div className="space-y-3" aria-busy="true">
          <div className="fd-skeleton h-9 w-64" />
          <div className="fd-skeleton h-24 w-full" />
          <div className="fd-skeleton h-56 w-full" />
        </div>
      </>
    );
  }

  if (!template) {
    return (
      <>
        <div className="fd-card">
          <EmptyState
            icon={RefreshCw}
            title="تعذر تحميل القالب"
            description={error ?? "تعذر تحميل تفاصيل القالب. أعد المحاولة."}
            action={
              <button type="button" className="fd-btn fd-btn-secondary h-11" onClick={reload}>
                إعادة المحاولة
              </button>
            }
          />
        </div>
      </>
    );
  }

  return (
    <>
      <div className="mx-auto max-w-[880px]">
        <nav aria-label="مسار التصفح" className="mb-3">
          <ol className="flex flex-wrap items-center gap-1 text-[12px] text-[var(--fd-ink-muted)]">
            <li>
              <Link href="/settings" className="hover:text-[var(--fd-ink)] hover:underline">
                الإعدادات
              </Link>
            </li>
            <li aria-hidden>
              <ChevronLeft size={14} className="rtl:rotate-180" />
            </li>
            <li>
              <Link
                href="/settings/templates"
                className="hover:text-[var(--fd-ink)] hover:underline"
              >
                قوالب الرسائل
              </Link>
            </li>
            <li aria-hidden>
              <ChevronLeft size={14} className="rtl:rotate-180" />
            </li>
            <li aria-current="page" className="text-[var(--fd-ink)]">
              الإصدار {template.version}
            </li>
          </ol>
        </nav>

        <PageHeader
          title={`${template.name} · الإصدار ${template.version}`}
          subtitle="عرض إصدار قالب رسالة. الحفظ ينشئ إصدارًا جديدًا."
        />

        {notice && (
          <div
            ref={noticeRef}
            tabIndex={-1}
            role="status"
            className="mb-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-green-soft)] px-4 py-3 text-[12px] text-[var(--fd-green-text)] focus:outline-none"
          >
            {notice}
          </div>
        )}

        <NoSendNotice className="mb-4" />

        <section className="fd-card fd-card-pad mb-4" aria-labelledby="template-meta">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 id="template-meta" className="text-sm font-semibold text-[var(--fd-ink)]">
              بيانات الإصدار
            </h2>
            {template.is_active ? (
              <StatusPill tone="green">نشط</StatusPill>
            ) : (
              <StatusPill tone="neutral">غير نشط</StatusPill>
            )}
          </div>
          <dl className="mt-3 grid gap-3 text-[12px] sm:grid-cols-2">
            <div>
              <dt className="text-[var(--fd-ink-subtle)]">القناة</dt>
              <dd className="mt-0.5">
                <bdi dir="ltr" lang="en">
                  {template.channel.toUpperCase()}
                </bdi>
              </dd>
            </div>
            <div>
              <dt className="text-[var(--fd-ink-subtle)]">اللغة</dt>
              <dd className="mt-0.5">العربية</dd>
            </div>
            <div>
              <dt className="text-[var(--fd-ink-subtle)]">أنشأه</dt>
              <dd className="mt-0.5">
                <bdi dir="auto">{template.created_by_name ?? "—"}</bdi>
              </dd>
            </div>
            <div>
              <dt className="text-[var(--fd-ink-subtle)]">تاريخ الإنشاء</dt>
              <dd className="mt-0.5 tabular-nums">
                <bdi dir="ltr">
                  {formatDateTime(template.created_at, {
                    locale: settings?.locale,
                    timeZone: settings?.timezone,
                  })}
                </bdi>
              </dd>
            </div>
          </dl>
        </section>

        <section className="fd-card fd-card-pad mb-4" aria-labelledby="template-body-title">
          <h2 id="template-body-title" className="text-sm font-semibold text-[var(--fd-ink)]">
            نص الرسالة
          </h2>
          <p className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">
            نص عادي كما حُفظ. تُستبدل المتغيرات عند إنشاء الحملة.
          </p>
          <div className="mt-2">
            <TemplateBody body={template.template_body} />
          </div>
        </section>

        {template.unknown_variables.length > 0 && (
          <section
            className="mb-4 rounded-[var(--fd-radius-card)] bg-[var(--fd-amber-soft)] p-4"
            aria-labelledby="template-unknown-title"
          >
            <h2
              id="template-unknown-title"
              className="flex items-center gap-2 text-[13px] font-semibold text-[var(--fd-amber-text)]"
            >
              <TriangleAlert size={16} aria-hidden />
              متغيرات غير معروفة
            </h2>
            <p className="mt-1 text-[12px] text-[var(--fd-amber-text)]">
              أزل هذه المتغيرات من النص قبل الاعتماد.{" "}
              {template.unknown_variables.map((variable, index) => (
                <span key={variable}>
                  {index > 0 ? "، " : ""}
                  <bdi dir="ltr" lang="en">{`{{${variable}}}`}</bdi>
                </span>
              ))}
            </p>
          </section>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <Link href="/settings/templates" className="fd-btn fd-btn-secondary h-11">
            العودة إلى القوالب
          </Link>
          {canManage && (
            <div className="flex flex-wrap items-center gap-2">
              {!template.is_active && (
                <button
                  type="button"
                  className="fd-btn fd-btn-secondary h-11"
                  onClick={() => {
                    setActivateError(null);
                    setActivateOpen(true);
                  }}
                >
                  <Power size={15} aria-hidden />
                  تفعيل هذا الإصدار
                </button>
              )}
              <Link
                href={`/settings/templates/new?from=${template.id}`}
                className="fd-btn fd-btn-primary h-11"
              >
                إصدار جديد من هذا النص
              </Link>
            </div>
          )}
        </div>
      </div>

      <ActivateVersionDialog
        template={activateOpen ? template : null}
        busy={activating}
        error={activateError}
        onClose={() => {
          if (activating) return;
          setActivateOpen(false);
          setActivateError(null);
        }}
        onConfirm={activate}
      />
    </>
  );
}
