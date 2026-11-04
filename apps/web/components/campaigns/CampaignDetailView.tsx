"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Ban,
  ChevronLeft,
  Lock,
  Megaphone,
  RefreshCw,
  Save,
  X,
} from "lucide-react";
import {
  ApiError,
  api,
  formatDateTime,
  formatDecimalString,
  type CampaignDetail,
  type CampaignNotice,
  type CampaignRecipient,
  type TemplateSummary,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { CampaignStatusPill } from "@/components/campaigns/CampaignStatusPill";
import { CampaignCounts } from "@/components/campaigns/CampaignCounts";
import { CampaignFacts } from "@/components/campaigns/CampaignFacts";
import { CampaignWarnings } from "@/components/campaigns/CampaignWarnings";
import { BlockingReasons } from "@/components/campaigns/BlockingReasons";
import { RecipientTable } from "@/components/campaigns/RecipientTable";
import { ExcludedTable } from "@/components/campaigns/ExcludedTable";
import { NoSendNotice } from "@/components/campaigns/NoSendNotice";
import { ProcessingNotice } from "@/components/campaigns/ProcessingNotice";
import { SnapshotCard } from "@/components/campaigns/SnapshotCard";
import { CampaignActionBar } from "@/components/campaigns/CampaignActionBar";
import { MessagePreviewDialog } from "@/components/campaigns/MessagePreviewDialog";
import { SubmitCampaignDialog } from "@/components/campaigns/SubmitCampaignDialog";
import { ApproveCampaignDialog } from "@/components/campaigns/ApproveCampaignDialog";
import { CancelCampaignDialog } from "@/components/campaigns/CancelCampaignDialog";
import { hasPermission, usePermissions } from "@/components/campaigns/permissions";
import { isStaleView, STALE_VIEW_MESSAGE } from "@/components/campaigns/campaign-format";
import { isProcessingCampaignStatus } from "@/components/campaigns/campaign-format";

function reasonsFromError(err: unknown): CampaignNotice[] | null {
  if (!(err instanceof ApiError) || err.code !== "CAMPAIGN_BLOCKED") return null;
  const value = err.details?.reasons;
  if (!Array.isArray(value)) return [];
  return value
    .filter(
      (item): item is CampaignNotice =>
        !!item && typeof item === "object" && "message_ar" in item,
    )
    .map((item) => ({ code: item.code, message_ar: item.message_ar, count: item.count }));
}

export function CampaignDetailView({
  campaignId,
  justCreated = false,
}: {
  campaignId: string;
  justCreated?: boolean;
}) {
  return (
    <Protected active="/campaigns">
      <CampaignDetailContent campaignId={campaignId} justCreated={justCreated} />
    </Protected>
  );
}

function CampaignDetailContent({
  campaignId,
  justCreated = false,
}: {
  campaignId: string;
  justCreated?: boolean;
}) {
  const { user, settings } = useSession();
  const permissions = usePermissions();
  const isAdmin = user.role === "admin";
  const canEdit = hasPermission(permissions, user.role, "campaigns.edit");
  const canSubmit = hasPermission(permissions, user.role, "campaigns.submit");
  const canApprove = hasPermission(permissions, user.role, "campaigns.approve");
  const canPreview = hasPermission(permissions, user.role, "campaigns.preview");

  const [detail, setDetail] = useState<CampaignDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [unknownVariables, setUnknownVariables] = useState<string[]>([]);
  const [editTemplates, setEditTemplates] = useState<TemplateSummary[]>([]);
  const noticeRef = useRef<HTMLDivElement>(null);

  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editTemplateId, setEditTemplateId] = useState("");
  const [editBusy, setEditBusy] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const editRef = useRef<HTMLDivElement>(null);

  const [submitOpen, setSubmitOpen] = useState(false);
  const [submitBusy, setSubmitBusy] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitBlocked, setSubmitBlocked] = useState<CampaignNotice[] | null>(null);

  const [approveOpen, setApproveOpen] = useState(false);
  const [approveBusy, setApproveBusy] = useState(false);
  const [approveError, setApproveError] = useState<string | null>(null);
  const [approveBlocked, setApproveBlocked] = useState<CampaignNotice[] | null>(null);

  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const [preview, setPreview] = useState<{
    recipients: CampaignRecipient[];
    initialIndex: number;
  } | null>(null);
  const [previewLoadingKey, setPreviewLoadingKey] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

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
    setLoadError(null);
    setNotFound(false);
    setForbidden(false);

    api
      .getCampaign(campaignId)
      .then((data) => {
        if (mounted) setDetail(data);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        } else if (err instanceof ApiError && err.status === 403) {
          setForbidden(true);
        } else {
          setLoadError(
            err instanceof ApiError ? err.messageAr : "تعذر تحميل تفاصيل الحملة.",
          );
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [campaignId, reloadKey]);

  useEffect(() => {
    if (!detail || !justCreated) return;
    setNotice("أُنشئت المسودة. راجع المستلمين والمبالغ قبل الإرسال للاعتماد.");
  }, [detail, justCreated]);

  useEffect(() => {
    if (notice) noticeRef.current?.focus();
  }, [notice]);

  useEffect(() => {
    if (!detail?.template_id) {
      setUnknownVariables([]);
      return;
    }
    if (!detail.blocking_reasons.some((reason) => reason.code === "UNRESOLVED_VARIABLES")) {
      setUnknownVariables([]);
      return;
    }
    let mounted = true;
    api
      .getTemplate(detail.template_id)
      .then((template) => {
        if (mounted) setUnknownVariables(template.unknown_variables ?? []);
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, [detail?.template_id, detail?.blocking_reasons]);

  useEffect(() => {
    if (!detail || !canEdit || detail.status !== "draft") return;
    let mounted = true;
    api
      .listTemplates({ active_only: true, page_size: 100 })
      .then((data) => {
        if (mounted) setEditTemplates(data.items ?? []);
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, [detail, canEdit]);

  const reload = useCallback(() => setReloadKey((key) => key + 1), []);

  const closeDialogs = useCallback(() => {
    setSubmitOpen(false);
    setApproveOpen(false);
    setCancelOpen(false);
    setSubmitError(null);
    setApproveError(null);
    setCancelError(null);
    setSubmitBlocked(null);
    setApproveBlocked(null);
  }, []);

  const handleActionError = useCallback(
    (err: unknown, fallback: string) => {
      if (isStaleView(err)) {
        setStale(true);
        closeDialogs();
        setReloadKey((key) => key + 1);
        return null;
      }
      if (err instanceof ApiError) {
        if (err.status === 403) {
          return "لا تملك صلاحية تنفيذ هذا الإجراء على هذه الحملة.";
        }
        return err.messageAr || fallback;
      }
      return fallback;
    },
    [closeDialogs],
  );

  async function handleSubmit() {
    if (!detail) return;
    setSubmitBusy(true);
    setSubmitError(null);
    setSubmitBlocked(null);
    try {
      const updated = await api.submitCampaign(detail.id, detail.revision);
      setDetail(updated);
      closeDialogs();
      setNotice("أُرسلت الحملة للاعتماد.");
    } catch (err) {
      const message = handleActionError(err, "تعذر الإرسال للاعتماد. أعد المحاولة.");
      if (message) {
        setSubmitError(message);
        setSubmitBlocked(reasonsFromError(err));
      }
    } finally {
      setSubmitBusy(false);
    }
  }

  async function handleApprove(acknowledgeWarnings: boolean) {
    if (!detail) return;
    setApproveBusy(true);
    setApproveError(null);
    setApproveBlocked(null);
    try {
      const wasApproved = detail.status === "approved";
      const updated = await api.approveCampaign(detail.id, {
        acknowledge_warnings: acknowledgeWarnings,
        expected_revision: detail.revision,
      });
      setDetail(updated);
      closeDialogs();
      setNotice(
        wasApproved || updated.status === "approved"
          ? "تم اعتماد الحملة وتثبيت نسختها."
          : "الحملة معتمدة مسبقًا.",
      );
    } catch (err) {
      const message = handleActionError(err, "تعذر اعتماد الحملة. أعد المحاولة.");
      if (message) {
        setApproveError(message);
        setApproveBlocked(reasonsFromError(err));
      }
    } finally {
      setApproveBusy(false);
    }
  }

  async function handleCancel(reason: string) {
    if (!detail) return;
    setCancelBusy(true);
    setCancelError(null);
    try {
      const updated = await api.cancelCampaign(detail.id, {
        reason: reason || null,
        expected_revision: detail.revision,
      });
      setDetail(updated);
      closeDialogs();
      setNotice("أُلغيت الحملة.");
    } catch (err) {
      const message = handleActionError(err, "تعذر إلغاء الحملة. أعد المحاولة.");
      if (message) setCancelError(message);
    } finally {
      setCancelBusy(false);
    }
  }

  async function openPreview(recipient: CampaignRecipient) {
    if (!detail || !canPreview || previewLoadingKey) return;
    setPreviewLoadingKey(recipient.key);
    setPreviewError(null);
    try {
      // Reveal only on explicit request; the page itself stays masked.
      const data = await api.previewCampaign(detail.id);
      const previewRecipients = data.recipients ?? [];
      const detailIndex = detail.recipients.findIndex(
        (item) => item.key === recipient.key,
      );
      let targetIndex = previewRecipients.findIndex(
        (item) => item.key === recipient.key,
      );
      if (targetIndex < 0) {
        targetIndex = detailIndex >= 0 ? detailIndex : 0;
      }
      if (previewRecipients.length === 0 || targetIndex < 0) {
        setPreviewError("تعذر تجهيز معاينة الرسالة لهذا المستلم.");
        return;
      }
      setPreview({
        recipients: previewRecipients,
        initialIndex: Math.min(targetIndex, previewRecipients.length - 1),
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setPreviewError("لا تملك صلاحية معاينة رسائل الحملة.");
      } else if (err instanceof ApiError && err.status === 404) {
        setPreviewError("لم نعد نجد هذه الحملة أو معاينتها.");
      } else {
        setPreviewError("تعذر تحميل معاينة الرسالة. أعد المحاولة.");
      }
    } finally {
      setPreviewLoadingKey(null);
    }
  }

  function startEditing() {
    if (!detail) return;
    setEditName(detail.name);
    setEditTemplateId(detail.template_id ?? "");
    setEditError(null);
    setEditing(true);
    requestAnimationFrame(() => {
      editRef.current?.scrollIntoView({ behavior: "auto", block: "center" });
      editRef.current?.querySelector<HTMLInputElement>("input")?.focus();
    });
  }

  async function saveEdit() {
    if (!detail) return;
    const trimmed = editName.trim();
    if (!trimmed) {
      setEditError("أدخل اسمًا للحملة.");
      return;
    }
    setEditBusy(true);
    setEditError(null);
    try {
      const payload: { name?: string; template_id?: string | null } = {};
      if (trimmed !== detail.name) payload.name = trimmed;
      if (editTemplateId && editTemplateId !== detail.template_id) {
        payload.template_id = editTemplateId;
      }
      if (Object.keys(payload).length === 0) {
        setEditing(false);
        return;
      }
      const updated = await api.updateCampaign(detail.id, payload);
      setDetail(updated);
      setEditing(false);
      setNotice("حُدِّثت المسودة وأُعيد حساب المعاينة.");
    } catch (err) {
      if (isStaleView(err)) {
        setStale(true);
        setEditing(false);
        setReloadKey((key) => key + 1);
      } else {
        setEditError(
          err instanceof ApiError
            ? err.messageAr
            : "تعذر حفظ التعديلات. أعد المحاولة.",
        );
      }
    } finally {
      setEditBusy(false);
    }
  }

  if (notFound) {
    return (
      <>
        <div className="fd-card">
          <EmptyState
            icon={Megaphone}
            title="لم نجد هذه الحملة"
            description="قد يكون الرابط قديمًا أو أن الحملة غير متاحة لحسابك."
            action={
              <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
                العودة إلى الحملات
              </Link>
            }
          />
        </div>
      </>
    );
  }

  if (forbidden) {
    return (
      <>
        <div className="fd-card">
          <EmptyState
            icon={Lock}
            title="لا تملك صلاحية عرض هذه الحملة."
            description="تواصل مع مدير النظام إن كنت تحتاج الوصول إلى هذه الحملة."
            action={
              <Link href="/campaigns" className="fd-btn fd-btn-secondary h-11">
                العودة إلى الحملات
              </Link>
            }
          />
        </div>
      </>
    );
  }

  if (loading && !detail) {
    return (
      <>
        <div className="space-y-4" aria-busy="true">
          <div className="fd-skeleton h-9 w-64" />
          <div className="fd-skeleton h-11 w-full" />
          <div className="grid grid-cols-3 gap-3">
            <div className="fd-skeleton h-20" />
            <div className="fd-skeleton h-20" />
            <div className="fd-skeleton h-20" />
          </div>
          <div className="fd-skeleton h-40 w-full" />
          <div className="fd-skeleton h-64 w-full" />
        </div>
      </>
    );
  }

  if (!detail) {
    return (
      <>
        <div className="fd-card">
          <EmptyState
            icon={RefreshCw}
            title="تعذر تحميل الحملة"
            description={loadError ?? "تعذر تحميل تفاصيل الحملة. أعد المحاولة."}
            action={
              <button
                type="button"
                className="fd-btn fd-btn-secondary h-11"
                onClick={reload}
              >
                إعادة المحاولة
              </button>
            }
          />
        </div>
      </>
    );
  }

  const status = detail.status;
  const approved = status === "approved";
  const cancelled = status === "cancelled";
  const draft = status === "draft";
  const awaiting = status === "awaiting_approval";
  const processing = isProcessingCampaignStatus(status);
  const totals = Object.entries(detail.totals_by_currency ?? {})
    .filter(([, amount]) => typeof amount === "string" && amount.trim() !== "")
    .sort(([a], [b]) => a.localeCompare(b));
  const firstBlocking = detail.blocking_reasons[0]?.message_ar ?? null;
  const showBar = draft || awaiting || approved;
  const messageCount =
    typeof detail.message_count === "number" && detail.message_count > 0
      ? detail.message_count
      : undefined;
  // D1: `approved` normally means nothing moved yet, but the derivation may lag;
  // if some recipients already left pending, do not claim nothing was sent.
  const processingStarted =
    processing ||
    (approved &&
      typeof detail.message_count === "number" &&
      detail.message_count > 0 &&
      typeof detail.pending_job_count === "number" &&
      detail.pending_job_count < detail.message_count);
  const frozen = approved || processing || (cancelled && !!detail.snapshot_hash);

  const editOptions: Array<{ id: string; name: string; version: number | null }> = [
    ...editTemplates.map((template) => ({
      id: template.id,
      name: template.name,
      version: template.version,
    })),
  ];
  if (
    detail.template_id &&
    !editOptions.some((option) => option.id === detail.template_id)
  ) {
    editOptions.unshift({
      id: detail.template_id,
      name: detail.template_name ?? "القالب الحالي",
      version: detail.template_version,
    });
  }

  return (
    <>
      <div className={showBar ? "pb-32" : ""}>
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
            <li aria-current="page" className="min-w-0 text-[var(--fd-ink)]">
              <bdi dir="auto" className="truncate">
                {detail.name}
              </bdi>
            </li>
          </ol>
        </nav>

        <div className="mb-4">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-[30px] font-bold leading-tight text-[var(--fd-ink)]">
              <bdi dir="auto">{detail.name}</bdi>
            </h1>
            <CampaignStatusPill status={status} />
          </div>
          <p className="mt-1 text-[14px] text-[var(--fd-ink-muted)]">
            القالب: <bdi dir="auto">{detail.template_name ?? "—"}</bdi>
            {detail.template_version != null && ` · الإصدار ${detail.template_version}`}
            {" · "}المصدر: <bdi dir="auto">{detail.source_filename ?? "—"}</bdi>
          </p>
          <p className="mt-1 text-[12px] text-[var(--fd-ink-subtle)]">
            أُنشئت <bdi dir="ltr">{formatted(detail.created_at)}</bdi>
            {detail.created_by_name && (
              <>
                {" "}
                بواسطة <bdi dir="auto">{detail.created_by_name}</bdi>
              </>
            )}
          </p>
          {approved && messageCount !== undefined && (
            <div className="mt-3">
              <Link
                href={`/campaigns/${detail.id}/results`}
                className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
              >
                نتائج الرسائل
              </Link>
            </div>
          )}
        </div>

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

        {stale && (
          <div
            role="alert"
            className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] px-4 py-3 text-[12px] text-[var(--fd-amber-text)]"
          >
            <span>{STALE_VIEW_MESSAGE}</span>
            <button
              type="button"
              className="fd-btn fd-btn-secondary h-11 px-3 text-[12px]"
              onClick={() => {
                setStale(false);
                reload();
              }}
            >
              تحديث
            </button>
          </div>
        )}

        {!approved && !cancelled && !processing && <NoSendNotice className="mb-4" />}

        {approved && (
          <div className="mb-4 space-y-3">
            <SnapshotCard
              campaign={detail}
              locale={settings?.locale}
              timeZone={settings?.timezone}
            />
            {processingStarted ? (
              <ProcessingNotice campaignId={detail.id} />
            ) : (
              <NoSendNotice density="full" />
            )}
          </div>
        )}

        {processing && (
          <div className="mb-4 space-y-3">
            <ProcessingNotice campaignId={detail.id} />
            <SnapshotCard
              campaign={detail}
              locale={settings?.locale}
              timeZone={settings?.timezone}
            />
          </div>
        )}

        {cancelled && <CancelledBanner campaign={detail} formatted={formatted} />}
        {cancelled && detail.snapshot_hash && (
          <div className="mb-4">
            <SnapshotCard
              campaign={detail}
              locale={settings?.locale}
              timeZone={settings?.timezone}
              muted
            />
          </div>
        )}

        <div className="mb-4">
          <CampaignCounts
            recipients={detail.recipient_count}
            excluded={detail.excluded_count}
            warnings={detail.warnings.length}
            messages={messageCount}
          />
        </div>

        {editing && draft && (
          <section
            ref={editRef}
            className="fd-card fd-card-pad mb-4"
            aria-labelledby="edit-draft-title"
          >
            <h2 id="edit-draft-title" className="text-sm font-semibold text-[var(--fd-ink)]">
              تعديل المسودة
            </h2>
            <div className="mt-3 grid gap-4 md:grid-cols-2">
              <div>
                <label htmlFor="edit-campaign-name" className="fd-label">
                  اسم الحملة
                </label>
                <input
                  id="edit-campaign-name"
                  className="fd-input h-11"
                  maxLength={120}
                  value={editName}
                  onChange={(event) => setEditName(event.target.value)}
                  disabled={editBusy}
                />
              </div>
              <div>
                <label htmlFor="edit-campaign-template" className="fd-label">
                  قالب الرسالة
                </label>
                <select
                  id="edit-campaign-template"
                  className="fd-input h-11"
                  value={editTemplateId}
                  onChange={(event) => setEditTemplateId(event.target.value)}
                  disabled={editBusy}
                >
                  {editOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.name}
                      {option.version != null ? ` — الإصدار ${option.version}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <p className="mt-2 text-[11px] text-[var(--fd-ink-subtle)]">
              لا يمكن تغيير الكشف بعد إنشاء الحملة. أنشئ حملة جديدة.
            </p>
            {editError && (
              <p role="alert" className="mt-2 text-[11px] text-[var(--fd-red-text)]">
                {editError}
              </p>
            )}
            <div className="mt-3 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="fd-btn fd-btn-secondary h-11"
                onClick={() => setEditing(false)}
                disabled={editBusy}
              >
                <X size={15} aria-hidden />
                إلغاء
              </button>
              <button
                type="button"
                className="fd-btn fd-btn-primary h-11"
                onClick={saveEdit}
                disabled={editBusy}
              >
                <Save size={15} aria-hidden />
                {editBusy ? "جارٍ الحفظ…" : "حفظ"}
              </button>
            </div>
          </section>
        )}

        <div className="mb-4 grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <section className="fd-card fd-card-pad" aria-labelledby="totals-title">
            <div className="flex items-center gap-2">
              <span className="h-4 w-1 rounded-full bg-[var(--fd-brand)]" aria-hidden />
              <h2 id="totals-title" className="text-sm font-semibold text-[var(--fd-ink)]">
                الإجماليات المستحقة
              </h2>
            </div>
            <p className="mt-1 text-[12px] text-[var(--fd-ink-subtle)]">
              لا تُجمع العملات معًا.
            </p>
            {totals.length === 0 ? (
              <p className="mt-3 text-[13px] text-[var(--fd-ink-subtle)]">—</p>
            ) : (
              <dl className="mt-3 space-y-1.5">
                {totals.map(([currency, amount]) => (
                  <div key={currency} className="flex items-baseline gap-2">
                    <dt className="text-[12px] text-[var(--fd-ink-subtle)]">
                      <bdi dir="ltr" lang="en">
                        {currency}
                      </bdi>
                    </dt>
                    <dd className="text-[18px] font-bold tabular-nums text-[var(--fd-ink)]">
                      <bdi dir="ltr">{formatDecimalString(amount)}</bdi>
                    </dd>
                  </div>
                ))}
              </dl>
            )}
          </section>

          <CampaignFacts
            campaign={detail}
            locale={settings?.locale}
            timeZone={settings?.timezone}
          />
        </div>

        {!approved && !cancelled && !processing && (
          <div className="mb-4">
            <CampaignWarnings
              warnings={detail.warnings}
              canApprove={canApprove}
            />
          </div>
        )}

        {(approved || processing) && detail.warnings.length > 0 && (
          <div className="mb-4">
            <CampaignWarnings warnings={detail.warnings} canApprove={canApprove} acknowledged />
          </div>
        )}

        {!cancelled && !processing && detail.blocking_reasons.length > 0 && (
          <div className="mb-4">
            <BlockingReasons
              reasons={detail.blocking_reasons}
              templateId={detail.template_id}
              unknownVariables={unknownVariables}
              isAdmin={isAdmin}
              canEdit={canEdit && draft}
              onShowExcluded={() =>
                document
                  .getElementById("excluded-panel")
                  ?.scrollIntoView({ behavior: "auto", block: "start" })
              }
              onChooseTemplate={startEditing}
            />
          </div>
        )}

        {previewError && (
          <p
            role="alert"
            className="mb-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] text-[var(--fd-red-text)]"
          >
            {previewError}
          </p>
        )}

        <div className="mb-4">
          <RecipientTable
            recipients={detail.recipients}
            campaignName={detail.name}
            frozen={frozen}
            showExcludedAction={detail.excluded.length > 0}
            canPreview={canPreview}
            previewLoadingKey={previewLoadingKey}
            onShowExcluded={() =>
              document
                .getElementById("excluded-panel")
                ?.scrollIntoView({ behavior: "auto", block: "start" })
            }
            onPreview={openPreview}
          />
        </div>

        <ExcludedTable
          excluded={detail.excluded}
          campaignName={detail.name}
          frozen={frozen}
        />
      </div>

      {showBar && (
        <CampaignActionBar
          campaign={detail}
          canEdit={canEdit && draft}
          canSubmit={canSubmit && draft}
          canApprove={canApprove}
          blockedReason={firstBlocking}
          locale={settings?.locale}
          timeZone={settings?.timezone}
          onEdit={startEditing}
          onSubmit={() => {
            setSubmitError(null);
            setSubmitBlocked(null);
            setSubmitOpen(true);
          }}
          onApprove={() => {
            setApproveError(null);
            setApproveBlocked(null);
            setApproveOpen(true);
          }}
          onCancel={() => {
            setCancelError(null);
            setCancelOpen(true);
          }}
        />
      )}

      {preview && canPreview && (
        <MessagePreviewDialog
          open
          recipients={preview.recipients}
          initialIndex={preview.initialIndex}
          onClose={() => setPreview(null)}
        />
      )}

      <SubmitCampaignDialog
        open={submitOpen}
        campaign={detail}
        busy={submitBusy}
        error={submitError}
        blockedReasons={submitBlocked}
        onClose={() => setSubmitOpen(false)}
        onConfirm={handleSubmit}
      />

      <ApproveCampaignDialog
        open={approveOpen}
        campaign={detail}
        busy={approveBusy}
        error={approveError}
        blockedReasons={approveBlocked}
        onClose={() => setApproveOpen(false)}
        onConfirm={handleApprove}
      />

      <CancelCampaignDialog
        open={cancelOpen}
        campaign={detail}
        busy={cancelBusy}
        error={cancelError}
        onClose={() => setCancelOpen(false)}
        onConfirm={handleCancel}
      />
    </>
  );
}

function CancelledBanner({
  campaign,
  formatted,
}: {
  campaign: CampaignDetail;
  formatted: (value: string | null) => string;
}) {
  return (
    <section
      className="mb-4 rounded-[var(--fd-radius-card)] border border-[var(--fd-line)] bg-[var(--fd-surface-alt)] p-5"
      aria-labelledby="cancelled-banner-title"
    >
      <div className="flex items-start gap-3">
        <Ban size={18} className="mt-0.5 shrink-0 text-[var(--fd-ink-muted)]" aria-hidden />
        <div className="min-w-0">
          <h2 id="cancelled-banner-title" className="text-[15px] font-bold text-[var(--fd-ink)]">
            أُلغيت هذه الحملة
          </h2>
          <p className="mt-1 text-[12px] text-[var(--fd-ink-muted)]">
            أُلغيت في <bdi dir="ltr">{formatted(campaign.cancelled_at)}</bdi>
          </p>
          {campaign.cancel_reason && (
            <p className="mt-2 text-[13px] leading-6 text-[var(--fd-ink)]">
              السبب: «{campaign.cancel_reason}»
            </p>
          )}
          <p className="mt-2 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
            النسخة المحفوظة للعرض فقط. لا يوجد إجراء إرسال أو إعادة إرسال.
          </p>
          {campaign.snapshot_hash && (
            <p className="mt-1 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
              أُلغيت الرسائل المعلّقة. بقيت نسخة المستلمين محفوظة.
            </p>
          )}
          <Link href="/campaigns" className="fd-btn fd-btn-secondary mt-3 h-11">
            العودة إلى الحملات
          </Link>
        </div>
      </div>
    </section>
  );
}
