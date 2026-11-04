"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Check, ChevronLeft, Minus, Plus, TriangleAlert } from "lucide-react";
import {
  ApiError,
  api,
  type ImportBatchSummary,
  type TemplateDetail,
  type TemplateSummary,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { NoSendNotice } from "@/components/campaigns/NoSendNotice";
import { ConfirmedImportPicker } from "@/components/campaigns/ConfirmedImportPicker";
import { TemplateBody } from "@/components/templates/TemplateBody";
import { hasPermission, usePermissions } from "@/components/campaigns/permissions";

const IMPORT_LIMIT = 8;
const NAME_MAX = 120;

function createErrorMessage(err: unknown): string {
  if (!(err instanceof ApiError)) {
    return "تعذر الاتصال بالخادم. تحقق من الشبكة وأعد المحاولة.";
  }
  switch (err.code) {
    case "IMPORT_NOT_CONFIRMED":
      return "هذا الكشف غير مؤكد. لا يمكن بناء حملة من كشف غير مؤكد.";
    case "NO_ACTIVE_TEMPLATE":
      return "لا يوجد قالب رسائل نشط. اطلب من مدير النظام تفعيل قالب ثم أعد المحاولة.";
    case "TEMPLATE_NOT_FOUND":
      return "القالب المحدد غير موجود. اختر قالبًا آخر.";
    default:
      break;
  }
  if (err.status === 403) return "لا تملك صلاحية إنشاء حملة.";
  if (err.status === 0) {
    return "تعذر الاتصال بالخادم. تحقق من الشبكة وأعد المحاولة.";
  }
  return err.messageAr || "تعذر إنشاء المسودة. أعد المحاولة.";
}

export function CampaignBuilder() {
  return (
    <Protected active="/campaigns">
      <CampaignBuilderContent />
    </Protected>
  );
}

function CampaignBuilderContent() {
  const router = useRouter();
  const { user, settings } = useSession();
  const permissions = usePermissions();
  const canCreate = hasPermission(permissions, user.role, "campaigns.create");
  const isAdmin = user.role === "admin";

  const [imports, setImports] = useState<ImportBatchSummary[]>([]);
  const [importsTotal, setImportsTotal] = useState<number | null>(null);
  const [importsLoading, setImportsLoading] = useState(true);
  const [importsError, setImportsError] = useState<string | null>(null);
  const [importsKey, setImportsKey] = useState(0);
  const [selectedImportId, setSelectedImportId] = useState("");

  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [templatesError, setTemplatesError] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [templateDetail, setTemplateDetail] = useState<TemplateDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setImportsLoading(true);
    setImportsError(null);

    Promise.all([
      api.listImports({ status: "confirmed", page_size: IMPORT_LIMIT }),
      api
        .listImports({ status: "confirmed", page_size: 1 })
        .catch(() => null),
    ])
      .then(([list, probe]) => {
        if (!mounted) return;
        setImports(list.items ?? []);
        setImportsTotal(probe?.total ?? list.total ?? null);
        setSelectedImportId((current) => current || list.items?.[0]?.id || "");
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setImports([]);
        setImportsTotal(null);
        setImportsError(
          err instanceof ApiError ? err.messageAr : "تعذر تحميل الكشوف المؤكدة.",
        );
      })
      .finally(() => {
        if (mounted) setImportsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [importsKey]);

  useEffect(() => {
    let mounted = true;
    setTemplatesLoading(true);
    setTemplatesError(null);

    Promise.all([
      api.listTemplates({ active_only: true, page_size: 100 }),
      api.getActiveTemplate().catch(() => null),
    ])
      .then(([list, active]) => {
        if (!mounted) return;
        setTemplates(list.items ?? []);
        const preferred =
          active?.id ?? list.items?.find((template) => template.is_active)?.id ?? "";
        setSelectedTemplateId(preferred);
        if (active) {
          setTemplateDetail(active);
        }
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setTemplates([]);
        setTemplatesError(
          err instanceof ApiError ? err.messageAr : "تعذر تحميل القوالب النشطة.",
        );
      })
      .finally(() => {
        if (mounted) setTemplatesLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedTemplateId) {
      setTemplateDetail(null);
      return;
    }
    const listed = templates.find((template) => template.id === selectedTemplateId);
    if (listed && templateDetail?.id === selectedTemplateId) return;

    let mounted = true;
    setDetailLoading(true);
    api
      .getTemplate(selectedTemplateId)
      .then((detail) => {
        if (mounted) setTemplateDetail(detail);
      })
      .catch(() => {
        if (mounted) setTemplateDetail(null);
      })
      .finally(() => {
        if (mounted) setDetailLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [selectedTemplateId, templates, templateDetail?.id]);

  const selectedTemplate =
    templates.find((template) => template.id === selectedTemplateId) ?? null;
  const unknownVariables = templateDetail?.unknown_variables ?? [];
  const trimmedName = name.trim();
  const hasImport = selectedImportId !== "";
  const hasTemplate = selectedTemplateId !== "";
  const ready = hasImport && trimmedName !== "" && hasTemplate;

  const disabledReason = useMemo(() => {
    if (importsLoading) return "جارٍ تحميل الكشوف المؤكدة…";
    if (templatesLoading) return "جارٍ تحميل القوالب…";
    if (imports.length === 0) return "اختر كشفًا مؤكدًا للبدء.";
    if (!hasImport) return "اختر كشفًا مؤكدًا للبدء.";
    if (!trimmedName) return "أدخل اسمًا للحملة.";
    if (!hasTemplate) return "لا يوجد قالب رسائل نشط.";
    return null;
  }, [importsLoading, templatesLoading, imports.length, hasImport, trimmedName, hasTemplate]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!trimmedName) {
      setNameError("أدخل اسمًا للحملة.");
      return;
    }
    setNameError(null);
    if (!hasImport || !hasTemplate) {
      setError("أكمل اختيار الكشف المؤكد وقالب الرسالة.");
      return;
    }

    setSaving(true);
    try {
      const created = await api.createCampaign({
        name: trimmedName,
        source_import_id: selectedImportId,
        template_id: selectedTemplateId,
      });
      router.push(`/campaigns/${created.id}?created=1`);
    } catch (err) {
      setError(createErrorMessage(err));
      setSaving(false);
    }
  }

  if (!canCreate) {
    return (
      <div className="fd-card">
        <EmptyState
          icon={Plus}
          title="لا تملك صلاحية إنشاء حملة"
          description="إنشاء الحملات متاح لحسابات الموظفين الإداريين. تواصل مع مدير النظام."
          action={
            <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
              العودة إلى الحملات
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <>
      <nav aria-label="مسار التصفح" className="mb-3">
        <ol className="flex flex-wrap items-center gap-1 text-[12px] text-[var(--fd-ink-muted)]">
          <li>
            <Link href="/campaigns" className="hover:text-[var(--fd-ink)] hover:underline">
              الحملات
            </Link>
          </li>
          <li aria-hidden>
            <ChevronLeft size={14} className="rtl:rotate-180" />
          </li>
          <li aria-current="page" className="text-[var(--fd-ink)]">
            حملة جديدة
          </li>
        </ol>
      </nav>

      <PageHeader
        title="حملة جديدة"
        subtitle="اختر كشفًا مؤكدًا وقالبًا، ثم أنشئ المسودة لمعاينة المستلمين."
      />
      <NoSendNotice className="mb-5" />

      <form onSubmit={submit} className="mx-auto max-w-[880px]" aria-busy={saving}>
        <section className="fd-card fd-card-pad mb-4" aria-labelledby="builder-import">
          <h2
            id="builder-import"
            className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--fd-ink)]"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--fd-brand-soft)] text-[12px] text-[var(--fd-brand)]">
              1
            </span>
            الكشف المؤكد
          </h2>
          <ConfirmedImportPicker
            imports={imports}
            total={importsTotal}
            loading={importsLoading}
            error={importsError}
            selectedId={selectedImportId}
            onSelect={setSelectedImportId}
            onRetry={() => setImportsKey((key) => key + 1)}
            locale={settings?.locale}
            timeZone={settings?.timezone}
          />
        </section>

        <section className="fd-card fd-card-pad mb-4" aria-labelledby="builder-name">
          <h2
            id="builder-name"
            className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--fd-ink)]"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--fd-brand-soft)] text-[12px] text-[var(--fd-brand)]">
              2
            </span>
            اسم الحملة
          </h2>
          <label htmlFor="campaign-name" className="fd-label">
            اسم الحملة
          </label>
          <input
            id="campaign-name"
            className="fd-input h-11"
            maxLength={NAME_MAX}
            placeholder="مثال: تذكير رسوم الفصل الأول"
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              setNameError(null);
            }}
            disabled={saving}
            aria-invalid={nameError ? true : undefined}
            aria-describedby={nameError ? "campaign-name-error" : "campaign-name-hint"}
            required
          />
          {nameError ? (
            <p
              id="campaign-name-error"
              role="alert"
              className="mt-1 text-[11px] text-[var(--fd-red-text)]"
            >
              {nameError}
            </p>
          ) : (
            <p id="campaign-name-hint" className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">
              يظهر في القائمة وفي سجل العمليات.
            </p>
          )}
        </section>

        <section className="fd-card fd-card-pad mb-4" aria-labelledby="builder-template">
          <h2
            id="builder-template"
            className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--fd-ink)]"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--fd-brand-soft)] text-[12px] text-[var(--fd-brand)]">
              3
            </span>
            قالب الرسالة
          </h2>

          {templatesLoading ? (
            <div className="fd-skeleton h-11 w-full" />
          ) : templates.length === 0 ? (
            <div className="rounded-[var(--fd-radius-control)] border border-[var(--fd-line)]">
              <EmptyState
                icon={TriangleAlert}
                title="لا يوجد قالب رسائل نشط"
                description="تحتاج الحملة إلى قالب نشط. اطلب من مدير النظام تفعيل قالب."
                action={
                  isAdmin ? (
                    <Link
                      href="/settings/templates"
                      className="fd-btn fd-btn-secondary h-11"
                    >
                      فتح القوالب
                    </Link>
                  ) : undefined
                }
              />
            </div>
          ) : (
            <>
              <label htmlFor="campaign-template" className="fd-label">
                قالب الرسالة
              </label>
              <select
                id="campaign-template"
                className="fd-input h-11"
                value={selectedTemplateId}
                onChange={(event) => setSelectedTemplateId(event.target.value)}
                disabled={saving}
              >
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name} — الإصدار {template.version}
                  </option>
                ))}
              </select>

              {unknownVariables.length > 0 && (
                <div className="mt-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] p-3 text-[12px] leading-6 text-[var(--fd-amber-text)]">
                  <p className="flex items-start gap-2">
                    <TriangleAlert size={15} className="mt-1 shrink-0" aria-hidden />
                    <span>
                      متغيرات غير معروفة في هذا القالب:{" "}
                      {unknownVariables.map((variable, index) => (
                        <span key={variable}>
                          {index > 0 ? "، " : ""}
                          <bdi dir="ltr" lang="en">{`{{${variable}}}`}</bdi>
                        </span>
                      ))}
                      . يمكن إنشاء المسودة، لكن لا يمكن اعتمادها قبل تصحيح القالب.
                    </span>
                  </p>
                  {isAdmin && selectedTemplate && (
                    <Link
                      href={`/settings/templates/${selectedTemplate.id}`}
                      className="mt-2 inline-flex min-h-11 items-center text-[12px] font-medium text-[var(--fd-brand)] hover:underline"
                    >
                      فتح القالب
                    </Link>
                  )}
                </div>
              )}

              <p className="mt-4 text-[11px] text-[var(--fd-ink-subtle)]">
                نص القالب كما هو. تُستبدل المتغيرات عند إنشاء المسودة.
              </p>
              <div className="mt-1">
                {detailLoading ? (
                  <div className="fd-skeleton h-32 w-full" />
                ) : templateDetail ? (
                  <TemplateBody
                    body={templateDetail.template_body}
                    className="max-h-[220px] overflow-y-auto"
                  />
                ) : (
                  <p className="rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] p-4 text-[12px] text-[var(--fd-ink-muted)]">
                    تعذر تحميل نص القالب. يمكنك المتابعة بالقالب المحدد.
                  </p>
                )}
              </div>
            </>
          )}

          {templatesError && (
            <p role="alert" className="mt-2 text-[11px] text-[var(--fd-red-text)]">
              {templatesError}
            </p>
          )}
        </section>

        <section
          className="rounded-[var(--fd-radius-card)] border border-[var(--fd-line)] bg-[var(--fd-surface-alt)] p-4"
          aria-labelledby="builder-checks"
        >
          <h2
            id="builder-checks"
            className="text-[12px] font-semibold text-[var(--fd-ink-muted)]"
          >
            قبل الإنشاء
          </h2>
          <ul className="mt-2 space-y-1.5 text-[12px]">
            <li className="flex items-center gap-2">
              {hasImport ? (
                <Check size={14} className="text-[var(--fd-green-text)]" aria-hidden />
              ) : (
                <Minus size={14} className="text-[var(--fd-ink-subtle)]" aria-hidden />
              )}
              {hasImport ? "تم اختيار كشف مؤكد" : "لم يُختر كشف مؤكد"}
            </li>
            <li className="flex items-center gap-2">
              {trimmedName ? (
                <Check size={14} className="text-[var(--fd-green-text)]" aria-hidden />
              ) : (
                <Minus size={14} className="text-[var(--fd-ink-subtle)]" aria-hidden />
              )}
              {trimmedName ? "الاسم جاهز" : "أدخل اسمًا للحملة"}
            </li>
            <li className="flex items-center gap-2">
              {hasTemplate ? (
                <Check size={14} className="text-[var(--fd-green-text)]" aria-hidden />
              ) : (
                <Minus size={14} className="text-[var(--fd-ink-subtle)]" aria-hidden />
              )}
              {selectedTemplate
                ? `${selectedTemplate.name} — الإصدار ${selectedTemplate.version}`
                : "لا يوجد قالب نشط"}
            </li>
          </ul>
        </section>

        {error && (
          <div
            role="alert"
            className="mt-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] text-[var(--fd-red-text)]"
          >
            <p>{error}</p>
            {error.includes("كشف") && (
              <Link
                href="/statements"
                className="mt-1 inline-flex min-h-11 items-center text-[12px] font-medium underline"
              >
                عرض الكشوف
              </Link>
            )}
          </div>
        )}

        <div className="sticky bottom-0 z-20 mt-6 flex flex-col gap-3 rounded-t-[var(--fd-radius-card)] border border-[var(--fd-line)] bg-[var(--fd-surface)]/95 px-4 py-4 shadow-[var(--fd-shadow-pop)] backdrop-blur sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-[12px] text-[var(--fd-ink-muted)]">لن تُرسل أي رسالة.</p>
            {disabledReason && (
              <p className="mt-0.5 text-[11px] text-[var(--fd-ink-subtle)]">
                {disabledReason} بعد الإنشاء تُحسب الاستحقاقات وتظهر المعاينة الكاملة.
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
              إلغاء
            </Link>
            <button
              type="submit"
              className="fd-btn fd-btn-primary h-11"
              disabled={saving || importsLoading || !ready}
            >
              <Plus size={15} aria-hidden />
              {saving ? "جارٍ إنشاء المسودة…" : "إنشاء المسودة"}
            </button>
          </div>
        </div>
      </form>
    </>
  );
}
