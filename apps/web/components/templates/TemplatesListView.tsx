"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { BookText, Plus, RefreshCw, TriangleAlert } from "lucide-react";
import {
  ApiError,
  api,
  formatNumber,
  type TemplateSummary,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { NoSendNotice } from "@/components/campaigns/NoSendNotice";
import { TemplateVersionList } from "@/components/templates/TemplateVersionList";
import { ActivateVersionDialog } from "@/components/templates/ActivateVersionDialog";
import { hasPermission, usePermissions } from "@/components/campaigns/permissions";

const PAGE_SIZE = 100;

export function TemplatesListView({ savedVersion }: { savedVersion: number | null }) {
  return (
    <Protected active="/settings">
      <TemplatesListContent savedVersion={savedVersion} />
    </Protected>
  );
}

function TemplatesListContent({ savedVersion }: { savedVersion: number | null }) {
  const { user, settings } = useSession();
  const permissions = usePermissions();
  const canView = hasPermission(permissions, user.role, "templates.view");
  const canManage = hasPermission(permissions, user.role, "templates.manage");

  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const noticeRef = useRef<HTMLDivElement>(null);

  const [activationTarget, setActivationTarget] = useState<TemplateSummary | null>(null);
  const [activating, setActivating] = useState(false);
  const [activateError, setActivateError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    api
      .listTemplates({ channel: "sms", page_size: PAGE_SIZE })
      .then((data) => {
        if (!mounted) return;
        setTemplates(data.items ?? []);
        setTotal(data.total ?? 0);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 403) {
          setError("لا تملك صلاحية عرض القوالب.");
        } else {
          setError(err instanceof ApiError ? err.messageAr : "تعذر تحميل القوالب.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [reloadKey]);

  useEffect(() => {
    if (savedVersion != null) {
      setNotice(`حُفظ الإصدار ${savedVersion} وأصبح نشطًا.`);
    }
  }, [savedVersion]);

  useEffect(() => {
    if (notice) noticeRef.current?.focus();
  }, [notice]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const unknowns = templates.filter((template) => template.unknown_variables.length > 0);

  async function confirmActivate() {
    if (!activationTarget) return;
    setActivating(true);
    setActivateError(null);
    try {
      const updated = await api.activateTemplate(activationTarget.id);
      setTemplates((current) =>
        current.map((template) =>
          template.name === updated.name
            ? { ...template, is_active: template.id === updated.id }
            : template,
        ),
      );
      setActivationTarget(null);
      setNotice(`فُعِّل الإصدار ${updated.version}.`);
    } catch (err) {
      setActivateError(
        err instanceof ApiError ? err.messageAr : "تعذر تفعيل الإصدار. أعد المحاولة.",
      );
    } finally {
      setActivating(false);
    }
  }

  if (!canView) {
    return (
      <>
        <PageHeader title="قوالب الرسائل" />
        <div className="fd-card">
          <EmptyState
            icon={BookText}
            title="لا تملك صلاحية عرض القوالب"
            description="عرض القوالب متاح للموظفين الإداريين. تواصل مع مدير النظام."
            action={
              <Link href="/settings" className="fd-btn fd-btn-secondary h-11">
                العودة إلى الإعدادات
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
        title="قوالب الرسائل"
        subtitle="نصوص رسائل التذكير وإصداراتها. كل حفظ ينشئ إصدارًا جديدًا."
        action={
          canManage ? (
            <Link href="/settings/templates/new" className="fd-btn fd-btn-primary h-11">
              <Plus size={16} aria-hidden />
              قالب جديد
            </Link>
          ) : undefined
        }
      />

      {!canManage && (
        <p className="mb-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] px-4 py-2 text-[12px] text-[var(--fd-ink-muted)]">
          العرض فقط — إدارة القوالب متاحة لمدير النظام.
        </p>
      )}

      <NoSendNotice className="mb-4" />

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

      {unknowns.length > 0 && (
        <p className="mb-4 flex items-start gap-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] px-4 py-3 text-[12px] leading-6 text-[var(--fd-amber-text)]">
          <TriangleAlert size={15} className="mt-1 shrink-0" aria-hidden />
          <span>
            إصدارات بها متغيرات غير معروفة لا يمكن استخدامها في حملة معتمدة.{" "}
            {unknowns.length === 1
              ? "إصدار واحد يحتاج مراجعة."
              : `${formatNumber(unknowns.length)} إصدارات تحتاج مراجعة.`}
          </span>
        </p>
      )}

      {error ? (
        <div
          role="alert"
          className="fd-card flex flex-wrap items-center justify-between gap-3 p-5"
        >
          <div>
            <p className="text-[13px] font-medium text-[var(--fd-ink)]">تعذر تحميل القوالب.</p>
            <p className="mt-1 text-[12px] text-[var(--fd-ink-muted)]">{error}</p>
          </div>
          <button
            type="button"
            className="fd-btn fd-btn-secondary h-11"
            onClick={reload}
          >
            <RefreshCw size={14} aria-hidden />
            إعادة المحاولة
          </button>
        </div>
      ) : loading ? (
        <div className="space-y-3" aria-busy="true">
          <div className="fd-skeleton h-28 w-full" />
          <div className="fd-skeleton h-28 w-full" />
        </div>
      ) : templates.length === 0 ? (
        <div className="fd-card">
          <EmptyState
            icon={BookText}
            title="لا توجد قوالب بعد"
            description={
              canManage
                ? "أنشئ قالب رسالة ليستخدمه إعداد الحملات."
                : "لم يُنشئ مدير النظام أي قالب رسائل بعد."
            }
            action={
              canManage ? (
                <Link
                  href="/settings/templates/new"
                  className="fd-btn fd-btn-secondary h-11"
                >
                  قالب جديد
                </Link>
              ) : undefined
            }
          />
        </div>
      ) : (
        <>
          <TemplateVersionList
            templates={templates}
            isAdmin={canManage}
            locale={settings?.locale}
            timeZone={settings?.timezone}
            activatingId={activating ? activationTarget?.id ?? null : null}
            onActivate={(template) => {
              setActivateError(null);
              setActivationTarget(template);
            }}
          />
          {total > templates.length && (
            <p className="mt-3 text-[11px] text-[var(--fd-ink-subtle)]">
              تُعرض {formatNumber(templates.length)} من {formatNumber(total)} قالبًا.
            </p>
          )}
        </>
      )}

      <ActivateVersionDialog
        template={activationTarget}
        busy={activating}
        error={activateError}
        onClose={() => {
          if (activating) return;
          setActivationTarget(null);
          setActivateError(null);
        }}
        onConfirm={confirmActivate}
      />
    </>
  );
}
