"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { BookText, ChevronLeft, RefreshCw } from "lucide-react";
import {
  ApiError,
  api,
  type TemplateDetail,
  type TemplateSummary,
  type TemplateVariable,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { NoSendNotice } from "@/components/campaigns/NoSendNotice";
import { TemplateEditor } from "@/components/templates/TemplateEditor";
import { hasPermission, usePermissions } from "@/components/campaigns/permissions";

export function TemplateEditorView({ fromId }: { fromId: string | null }) {
  return (
    <Protected active="/settings">
      <TemplateEditorContent fromId={fromId} />
    </Protected>
  );
}

function TemplateEditorContent({ fromId }: { fromId: string | null }) {
  const router = useRouter();
  const { user } = useSession();
  const permissions = usePermissions();
  const canManage = hasPermission(permissions, user.role, "templates.manage");

  const [fromTemplate, setFromTemplate] = useState<TemplateDetail | null>(null);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [variables, setVariables] = useState<TemplateVariable[]>([]);
  const [variablesError, setVariablesError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setLoadError(null);
    setVariablesError(null);

    Promise.all([
      api
        .getTemplateVariables()
        .then((data) => {
          if (mounted) setVariables(data.variables ?? []);
        })
        .catch(() => {
          if (mounted) {
            setVariables([]);
            setVariablesError("تعذر تحميل المتغيرات.");
          }
        }),
      api
        .listTemplates({ page_size: 100 })
        .then((data) => {
          if (mounted) setTemplates(data.items ?? []);
        })
        .catch(() => undefined),
      fromId
        ? api.getTemplate(fromId).then((data) => {
            if (mounted) setFromTemplate(data);
          })
        : Promise.resolve(),
    ])
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 404) {
          setLoadError("لم نجد القالب المصدر. اختر قالبًا من القائمة.");
        } else {
          setLoadError(err instanceof ApiError ? err.messageAr : "تعذر تحميل القالب.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [fromId, reloadKey]);

  const activeName = fromTemplate?.name ?? null;
  const nextVersion = useMemo(() => {
    if (fromId) {
      if (!fromTemplate) return null;
      const siblings = templates.filter((template) => template.name === fromTemplate.name);
      const max = siblings.reduce(
        (value, template) => Math.max(value, template.version),
        fromTemplate.version,
      );
      return max + 1;
    }
    return null;
  }, [fromId, fromTemplate, templates]);

  async function save(payload: { name: string; body: string }) {
    setSaving(true);
    setError(null);
    try {
      const created = await api.createTemplate({
        name: payload.name,
        language: "ar",
        channel: "sms",
        template_body: payload.body,
      });
      router.push(`/settings/templates?saved=${created.version}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("لا تملك صلاحية إدارة القوالب.");
      } else if (err instanceof ApiError) {
        setError(err.messageAr || "تعذر حفظ القالب. أعد المحاولة.");
      } else {
        setError("تعذر حفظ القالب. أعد المحاولة.");
      }
      setSaving(false);
    }
  }

  if (!canManage) {
    return (
      <>
        <div className="fd-card">
          <EmptyState
            icon={BookText}
            title="إدارة القوالب متاحة لمدير النظام."
            description="يمكنك عرض القوالب وإصداراتها من قائمة القوالب."
            action={
              <Link href="/settings/templates" className="fd-btn fd-btn-secondary h-11">
                العرض فقط
              </Link>
            }
          />
        </div>
      </>
    );
  }

  if (loading) {
    return (
      <>
        <div className="space-y-3" aria-busy="true">
          <div className="fd-skeleton h-9 w-64" />
          <div className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
            <div className="fd-skeleton h-96 w-full" />
            <div className="fd-skeleton h-64 w-full" />
          </div>
        </div>
      </>
    );
  }

  if (loadError) {
    return (
      <>
        <div className="fd-card">
          <EmptyState
            icon={RefreshCw}
            title="تعذر تحميل القالب"
            description={loadError}
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <button
                  type="button"
                  className="fd-btn fd-btn-secondary h-11"
                  onClick={() => setReloadKey((key) => key + 1)}
                >
                  إعادة المحاولة
                </button>
                <Link href="/settings/templates" className="fd-btn fd-btn-secondary h-11">
                  العودة إلى القوالب
                </Link>
              </div>
            }
          />
        </div>
      </>
    );
  }

  return (
    <>
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
            {fromTemplate ? "إصدار جديد" : "قالب جديد"}
          </li>
        </ol>
      </nav>

      <PageHeader
        title={fromTemplate ? `إصدار جديد من «${fromTemplate.name}»` : "قالب جديد"}
        subtitle="اكتب نص الرسالة وأدرج المتغيرات. الحفظ ينشئ إصدارًا جديدًا ويجعله نشطًا."
      />
      <NoSendNotice className="mb-4" />

      {activeName && (
        <p className="mb-4 text-[12px] text-[var(--fd-ink-muted)]">
          المصدر: <bdi dir="auto">{activeName}</bdi> · الإصدار{" "}
          {fromTemplate?.version ?? "—"}
        </p>
      )}

      <TemplateEditor
        fromTemplate={fromTemplate}
        nextVersion={nextVersion}
        variables={variables}
        variablesError={variablesError}
        saving={saving}
        error={error}
        onSave={save}
      />
    </>
  );
}
