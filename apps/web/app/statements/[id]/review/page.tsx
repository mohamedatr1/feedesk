"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, Fragment } from "react";
import {
  ArrowLeft,
  Ban,
  CheckCircle2,
  ExternalLink,
  LoaderCircle,
  Pencil,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  TriangleAlert,
  UserRoundSearch,
  X,
} from "lucide-react";
import {
  ApiError,
  ambiguousGuardianRowIds,
  api,
  formatDateTime,
  formatDecimalString,
  formatNumber,
  importErrorMessage,
  importSourceFileUrl,
  type GuardianCandidateRow,
  type GuardianCandidatesResponse,
  type GuardianResolution,
  type ImportDetail,
  type StagedRow,
  type StagedRowData,
} from "@/lib/api";
import { useSession } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { Dialog } from "@/components/Dialog";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ImportCounts } from "@/components/imports/ImportCounts";
import { ImportStatusPill } from "@/components/imports/ImportStatusPill";
import { IssueList } from "@/components/imports/IssueList";
import { RowIssues } from "@/components/imports/RowIssues";
import { StagedRowStatusPill } from "@/components/imports/StagedRowStatusPill";
import { TablePager } from "@/components/imports/TablePager";
import { CurrencyTotals } from "@/components/imports/CurrencyTotals";
import { AmbiguousGuardianNotice } from "@/components/imports/AmbiguousGuardianNotice";
import { BulkExclusionBar } from "@/components/imports/BulkExclusionBar";
import { GuardianResolutionBadge } from "@/components/imports/GuardianResolutionBadge";
import { GuardianResolutionDialog } from "@/components/imports/GuardianResolutionDialog";
import {
  guardianCountsSummary,
  needsGuardianResolution,
  rowsNeedResolution,
} from "@/components/imports/guardian-format";

const PAGE_SIZE = 50;

type BulkAction = {
  kind: "exclude" | "restore";
  scope: "selected" | "invalid";
};

type EditableField =
  | "guardian_name"
  | "guardian_phone_original"
  | "student_name"
  | "amount_paid"
  | "remaining_balance"
  | "currency"
  | "fee_period";

type Draft = Partial<Record<EditableField, string>>;

const FILTER_OPTIONS = [
  { value: "", label: "الكل" },
  { value: "valid", label: "صالحة" },
  { value: "warning", label: "تحذيرات" },
  { value: "invalid", label: "أخطاء" },
  { value: "excluded", label: "مستثناة" },
];

function originalValue(row: StagedRow, field: EditableField): string {
  const data = row.normalized_data;
  if (field === "guardian_phone_original") {
    return data.guardian_phone_original ?? data.guardian_phone_normalized ?? "";
  }
  if (field === "guardian_name") return data.guardian_name ?? "";
  if (field === "student_name") return data.student_name ?? "";
  if (field === "amount_paid") return data.amount_paid ?? "";
  if (field === "remaining_balance") return data.remaining_balance ?? "";
  if (field === "currency") return data.currency ?? "";
  return data.fee_period ?? "";
}

function amountText(value: string | null | undefined): string {
  if (!value || value.trim() === "") return "—";
  return formatDecimalString(value);
}

function bigid(value: string | null | undefined): string {
  if (!value || value.trim() === "") return "—";
  return value;
}

/** Arabic counted noun for bulk copy: "سطر واحد", "7 أسطر", "12 سطرًا". */
function rowNoun(count: number): string {
  if (count === 1) return "سطر واحد";
  if (count === 2) return "سطرين";
  const rule = new Intl.PluralRules("ar").select(count);
  if (rule === "few") return `${formatNumber(count)} أسطر`;
  return `${formatNumber(count)} سطرًا`;
}

function issueLabel(code: string): string | null {
  if (code === "MISSING_PHONE") return "مفقود";
  if (code === "INVALID_PHONE") return "غير صالح";
  return null;
}

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.messageAr : fallback;
}

function ReviewContent() {
  const params = useParams<{ id: string }>();
  const importId = typeof params.id === "string" ? params.id : "";
  const router = useRouter();
  const { user, settings } = useSession();
  const tableRef = useRef<HTMLElement>(null);

  const [detail, setDetail] = useState<ImportDetail | null>(null);
  const [rows, setRows] = useState<StagedRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState("");

  const [loadingDetail, setLoadingDetail] = useState(true);
  const [loadingRows, setLoadingRows] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rowsError, setRowsError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [warningRows, setWarningRows] = useState<number | null>(null);

  const [editingRowId, setEditingRowId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>({});
  const [rowSaving, setRowSaving] = useState<string | null>(null);
  const [rowErrors, setRowErrors] = useState<Record<string, string | null>>({});

  const [acknowledged, setAcknowledged] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const [detailVersion, setDetailVersion] = useState(0);
  const [rowsVersion, setRowsVersion] = useState(0);

  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [bulkAction, setBulkAction] = useState<BulkAction | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkError, setBulkError] = useState<string | null>(null);

  const [guardianData, setGuardianData] = useState<GuardianCandidatesResponse | null>(null);
  const [guardianLoading, setGuardianLoading] = useState(false);
  const [guardianError, setGuardianError] = useState<string | null>(null);
  const [guardianVersion, setGuardianVersion] = useState(0);
  const [guardianTarget, setGuardianTarget] = useState<GuardianCandidateRow | null>(null);
  const [guardianSaving, setGuardianSaving] = useState(false);
  const [guardianSaveError, setGuardianSaveError] = useState<string | null>(null);

  const [ambiguousIds, setAmbiguousIds] = useState<string[]>([]);
  const [ambiguousRows, setAmbiguousRows] = useState<GuardianCandidateRow[]>([]);
  const [confirmAmbiguous, setConfirmAmbiguous] = useState<string[] | null>(null);

  const selectAllRef = useRef<HTMLInputElement>(null);
  const ambiguousActionRef = useRef<HTMLButtonElement>(null);

  const reviewable =
    detail?.status === "review_required" || detail?.status === "ready_to_confirm";

  const refresh = useCallback(() => {
    setDetailVersion((value) => value + 1);
    setRowsVersion((value) => value + 1);
  }, []);

  useEffect(() => {
    if (!importId) return;
    let mounted = true;
    setLoadingDetail(true);
    setError(null);

    api
      .getImport(importId)
      .then((data) => {
        if (!mounted) return;
        setDetail(data);
        if (
          data.status !== "review_required" &&
          data.status !== "ready_to_confirm"
        ) {
          setEditingRowId(null);
          setDraft({});
        }
        return api
          .listImportRows(importId, { page: 1, page_size: 1, status: "warning" })
          .then((warningPage) => {
            if (mounted) setWarningRows(warningPage.total ?? 0);
          })
          .catch(() => {
            if (mounted) setWarningRows(0);
          });
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 404) {
          setError("لم نجد هذا الكشف. قد يكون الرابط قديمًا أو أن الكشف غير متاح لحسابك.");
        } else if (err instanceof ApiError && err.status === 403) {
          setError("لا تملك صلاحية مراجعة هذا الكشف.");
        } else {
          setError(errorMessage(err, "تعذر تحميل بيانات الاستيراد."));
        }
      })
      .finally(() => {
        if (mounted) setLoadingDetail(false);
      });

    return () => {
      mounted = false;
    };
  }, [importId, detailVersion]);

  useEffect(() => {
    if (!importId) return;
    let mounted = true;
    setLoadingRows(true);
    setRowsError(null);

    api
      .listImportRows(importId, {
        page,
        page_size: PAGE_SIZE,
        status: filter as "" | "valid" | "warning" | "invalid" | "excluded",
        q: query,
      })
      .then((data) => {
        if (!mounted) return;
        setRows(data.items ?? []);
        setTotal(data.total ?? 0);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setRowsError(errorMessage(err, "تعذر تحميل أسطر الكشف."));
      })
      .finally(() => {
        if (mounted) setLoadingRows(false);
      });

    return () => {
      mounted = false;
    };
  }, [importId, page, filter, query, rowsVersion]);

  // Guardian matching is secondary to the ledger: when the endpoint is not
  // available, the review screen still works and simply shows no row action.
  useEffect(() => {
    if (!importId || !reviewable) {
      setGuardianData(null);
      setGuardianError(null);
      setGuardianLoading(false);
      return;
    }
    let mounted = true;
    setGuardianLoading(true);
    setGuardianError(null);

    api
      .getGuardianCandidates(importId)
      .then((data) => {
        if (mounted) setGuardianData(data);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setGuardianData(null);
        if (err instanceof ApiError && (err.status === 403 || err.status === 404)) return;
        setGuardianError(errorMessage(err, "تعذر تحميل مطابقات أولياء الأمور."));
      })
      .finally(() => {
        if (mounted) setGuardianLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [importId, reviewable, guardianVersion]);

  // Selection belongs to one filtered page; changing the view clears it.
  useEffect(() => {
    setSelected(new Set());
  }, [page, filter, query]);

  const pageIds = rows.map((row) => row.id);
  const allSelected = pageIds.length > 0 && pageIds.every((id) => selected.has(id));
  const someSelected = !allSelected && pageIds.some((id) => selected.has(id));

  useEffect(() => {
    if (selectAllRef.current) selectAllRef.current.indeterminate = someSelected;
  }, [someSelected]);

  // The confirm button becomes disabled when confirmation is refused, so move
  // focus to the refusal block instead of dropping it on the document.
  useEffect(() => {
    if (confirmAmbiguous !== null) ambiguousActionRef.current?.focus();
  }, [confirmAmbiguous]);

  const editing = editingRowId !== null;
  const dirty = Object.keys(draft).length > 0;

  function guardEditing(action: () => void): boolean {
    if (editingRowId && dirty) {
      setNotice("احفظ التعديل أو ألغِه أولًا.");
      return false;
    }
    action();
    return true;
  }

  function beginEdit(row: StagedRow) {
    if (editingRowId === row.id) return;
    if (editingRowId && dirty) {
      setNotice("احفظ التعديل أو ألغِه أولًا.");
      return;
    }
    setEditingRowId(row.id);
    setDraft({});
    setRowErrors((current) => ({ ...current, [row.id]: null }));
  }

  function cancelEdit() {
    setEditingRowId(null);
    setDraft({});
  }

  function updateDraft(row: StagedRow, field: EditableField, value: string) {
    const baseline = originalValue(row, field);
    setDraft((current) => {
      const next = { ...current };
      if (value === baseline) {
        delete next[field];
      } else {
        next[field] = value;
      }
      return next;
    });
  }

  async function saveRow(row: StagedRow) {
    if (Object.keys(draft).length === 0) {
      cancelEdit();
      return;
    }
    setRowSaving(row.id);
    setRowErrors((current) => ({ ...current, [row.id]: null }));
    try {
      const updated = await api.updateImportRow(importId, row.id, {
        normalized_data: draft as StagedRowData,
      });
      setRows((current) => current.map((item) => (item.id === row.id ? updated : item)));
      setEditingRowId(null);
      setDraft({});
      setNotice("تم تحديث السجل وأُعيد التحقق منه.");
      refresh();
      window.requestAnimationFrame(() => {
        document.getElementById(`edit-${row.id}`)?.focus();
      });
    } catch (err) {
      setRowErrors((current) => ({
        ...current,
        [row.id]: errorMessage(err, "تعذر حفظ تعديلات السجل."),
      }));
    } finally {
      setRowSaving(null);
    }
  }

  async function toggleExclusion(row: StagedRow) {
    if (!guardEditing(() => undefined)) return;
    setRowSaving(row.id);
    setRowErrors((current) => ({ ...current, [row.id]: null }));
    try {
      await api.updateImportRow(importId, row.id, { is_excluded: !row.is_excluded });
      setNotice(
        row.is_excluded
          ? "تمت استعادة السجل."
          : "تم استثناء السجل. لن يدخل أي حملة.",
      );
      refresh();
    } catch (err) {
      setRowErrors((current) => ({
        ...current,
        [row.id]: errorMessage(err, "تعذر تغيير حالة استثناء السجل."),
      }));
    } finally {
      setRowSaving(null);
    }
  }

  async function confirmImport() {
    if (!detail) return;
    setConfirming(true);
    setConfirmError(null);
    setConfirmAmbiguous(null);
    try {
      await api.confirmImport(importId, acknowledged);
      setConfirmOpen(false);
      setAmbiguousIds([]);
      setAmbiguousRows([]);
      router.push(`/statements/${detail.id}?confirmed=1`);
    } catch (err) {
      const ids = ambiguousGuardianRowIds(err);
      if (ids) {
        // Refused, not confirmed. Keep the dialog open with a dedicated block
        // and remember which rows need a decision.
        setConfirmAmbiguous(ids);
        setAmbiguousIds(ids);
        setAmbiguousRows([]);
        api
          .getGuardianCandidates(importId)
          .then((data) => {
            setGuardianData(data);
            setAmbiguousRows((data.items ?? []).filter((item) => ids.includes(item.row_id)));
          })
          .catch(() => undefined);
        return;
      }
      setConfirmError(errorMessage(err, "تعذر تأكيد الاستيراد."));
    } finally {
      setConfirming(false);
    }
  }

  const confirmed = detail?.status === "confirmed";
  const cancelled = detail?.status === "cancelled";
  const failed = detail?.status === "failed";
  const processing = detail?.status === "processing";
  const uploaded = detail?.status === "uploaded";
  const showTable = !failed && !processing && !uploaded;
  const showCounts = !failed && !processing && !uploaded;
  const columnCount = reviewable ? 10 : 9;

  const totalRows = detail?.total_rows ?? 0;
  const validRows = detail?.valid_rows ?? 0;
  const invalidRows = detail?.invalid_rows ?? 0;
  const excludedRows = detail?.excluded_rows ?? null;
  const includedRows = Math.max(
    totalRows - (excludedRows ?? 0) - invalidRows,
    0,
  );

  const hasWarnings = Boolean(
    detail &&
      ((detail.warnings ?? []).length > 0 ||
        (warningRows ?? 0) > 0 ||
        rows.some((row) => row.validation_status === "warning")),
  );
  const visibleBlockingRows = rows.some(
    (row) => !row.is_excluded && row.validation_status === "invalid",
  );
  const blocking = invalidRows > 0 || visibleBlockingRows;

  let blockedReason: string | null = null;
  if (!reviewable) {
    blockedReason = null;
  } else if (blocking) {
    blockedReason =
      invalidRows > 0
        ? `لا يمكن التأكيد: ${formatNumber(invalidRows)} سجل به أخطاء. صحّحها أو استثنِها.`
        : "لا يمكن التأكيد: يوجد سجل به أخطاء في هذه الصفحة. صحّحه أو استثنِه.";
  } else if (hasWarnings && !acknowledged) {
    blockedReason = "أكّد أنك راجعت التحذيرات للمتابعة.";
  } else if (warningRows === null) {
    blockedReason = "جارٍ التحقق من التحذيرات…";
  } else if (includedRows === 0) {
    blockedReason = "لا توجد سجلات قابلة للتأكيد. استعد سجلًا واحدًا على الأقل.";
  } else if (rowSaving) {
    blockedReason = "جارٍ حفظ التعديل…";
  } else if (confirming) {
    blockedReason = "جارٍ التأكيد…";
  }

  const canConfirm =
    Boolean(detail) &&
    reviewable &&
    !blocking &&
    (!hasWarnings || acknowledged) &&
    (hasWarnings || warningRows !== null) &&
    includedRows > 0 &&
    !rowSaving &&
    !confirming &&
    confirmAmbiguous === null;

  const guardianByRow = new Map(
    (guardianData?.items ?? []).map((item) => [item.row_id, item]),
  );
  const guardianSummary = guardianData?.counts
    ? guardianCountsSummary(guardianData.counts)
    : [];

  const sourceUrl = importSourceFileUrl(detail?.source_file_id);
  const uploader =
    detail?.uploaded_by_name ??
    (detail?.uploaded_by
      ? detail.uploaded_by === user.id
        ? user.username
        : detail.uploaded_by.slice(0, 8)
      : "—");

  const selectionDisabled = !reviewable || editing || Boolean(rowSaving) || bulkBusy;

  function toggleRow(rowId: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(rowId)) next.delete(rowId);
      else next.add(rowId);
      return next;
    });
  }

  function toggleAllRows() {
    setSelected((current) => {
      const next = new Set(current);
      if (pageIds.every((id) => next.has(id))) {
        pageIds.forEach((id) => next.delete(id));
      } else {
        pageIds.forEach((id) => next.add(id));
      }
      return next;
    });
  }

  function clearSelection() {
    setSelected(new Set());
  }

  function openBulk(action: BulkAction) {
    if (!guardEditing(() => undefined)) return;
    setBulkError(null);
    setBulkAction(action);
  }

  async function runBulkAction() {
    if (!bulkAction) return;
    const rowIds = bulkAction.scope === "selected" ? Array.from(selected) : [];
    const isExclude = bulkAction.kind === "exclude";

    setBulkBusy(true);
    setBulkError(null);
    try {
      const updated = await api.setImportRowsExclusion(importId, {
        is_excluded: isExclude,
        scope: bulkAction.scope,
        row_ids: rowIds,
      });

      setDetail(updated);
      setSelected(new Set());
      setBulkAction(null);
      setAmbiguousIds([]);
      setAmbiguousRows([]);
      setConfirmAmbiguous(null);

      const target =
        bulkAction.scope === "invalid" ? "الصفوف غير الصالحة" : "الأسطر المحددة";
      const counts =
        updated.excluded_rows !== null && updated.excluded_rows !== undefined
          ? ` المستثناة الآن ${formatNumber(updated.excluded_rows)} من ${formatNumber(updated.total_rows)}.`
          : "";
      setNotice(`${isExclude ? "تم استثناء" : "تمت استعادة"} ${target}.${counts}`);

      refresh();
      setGuardianVersion((value) => value + 1);
    } catch (err) {
      setBulkError(errorMessage(err, "تعذر تحديث استثناء الأسطر."));
    } finally {
      setBulkBusy(false);
    }
  }

  const bulkDialog = bulkAction
    ? {
        title:
          bulkAction.scope === "invalid"
            ? `استثناء الصفوف غير الصالحة (${formatNumber(invalidRows)})؟`
            : bulkAction.kind === "restore"
              ? `استعادة ${rowNoun(selected.size)}؟`
              : `استثناء ${rowNoun(selected.size)}؟`,
        description:
          bulkAction.scope === "invalid"
            ? "سيُستثنى كل سطر به أخطاء في هذا الكشف، وليس في هذه الصفحة فقط. راجع الأسطر قبل المتابعة."
            : bulkAction.kind === "restore"
              ? "ستعود الأسطر المحددة إلى الاستيراد عند التأكيد. يمكنك استثناءها مجددًا قبل التأكيد."
              : "لن تدخل الأسطر المحددة أي حملة. يمكنك استعادتها قبل التأكيد.",
        confirmLabel:
          bulkAction.scope === "invalid"
            ? "استثناء الصفوف غير الصالحة"
            : bulkAction.kind === "restore"
              ? "استعادة المحدد"
              : "استثناء المحدد",
        tone: bulkAction.kind === "restore" ? ("primary" as const) : ("danger" as const),
      }
    : null;

  function openGuardian(item: GuardianCandidateRow) {
    if (!guardEditing(() => undefined)) return;
    setGuardianSaveError(null);
    setGuardianTarget(item);
  }

  async function saveGuardianResolution(resolution: GuardianResolution) {
    const target = guardianTarget;
    if (!target) return;

    setGuardianSaving(true);
    setGuardianSaveError(null);
    try {
      const updated = await api.updateImportRow(importId, target.row_id, {
        guardian_resolution: resolution,
      });
      setRows((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setGuardianTarget(null);
      setNotice("تم حفظ تحديد ولي الأمر لهذا السطر.");
      setAmbiguousIds((current) => current.filter((id) => id !== target.row_id));
      setAmbiguousRows((current) =>
        current.filter((item) => item.row_id !== target.row_id),
      );
      setConfirmAmbiguous(null);
      setGuardianVersion((value) => value + 1);
      refresh();
      window.requestAnimationFrame(() => {
        document.getElementById(`row-${target.row_id}`)?.focus({ preventScroll: true });
      });
    } catch (err) {
      setGuardianSaveError(errorMessage(err, "تعذر حفظ تحديد ولي الأمر."));
    } finally {
      setGuardianSaving(false);
    }
  }

  /** Focus the affected row when it is on this page, otherwise search by name. */
  function revealRow(rowId: string, guardianName: string) {
    guardEditing(() => {
      const element = document.getElementById(`row-${rowId}`);
      if (element) {
        element.scrollIntoView({ block: "center" });
        element.focus({ preventScroll: true });
        return;
      }

      const name = guardianName.trim();
      if (!name) {
        document.getElementById("ambiguous-guardian-notice")?.scrollIntoView({ block: "start" });
        return;
      }

      setSearchInput(name);
      setQuery(name);
      setFilter("");
      setPage(1);
      setNotice("عرضنا نتائج البحث عن ولي الأمر المتأثر.");
    });
  }

  function closeConfirmDialog() {
    if (confirming) return;
    setConfirmOpen(false);
    setConfirmError(null);
    setConfirmAmbiguous(null);
  }

  function showAffectedRows() {
    closeConfirmDialog();
    window.requestAnimationFrame(() => {
      const firstId = ambiguousIds[0];
      if (firstId) {
        const row = ambiguousRows.find((item) => item.row_id === firstId);
        revealRow(firstId, row?.guardian_name ?? "");
      } else {
        document
          .getElementById("ambiguous-guardian-notice")
          ?.scrollIntoView({ block: "start" });
      }
    });
  }

  function focusInvalid() {
    guardEditing(() => {
      setFilter("invalid");
      setPage(1);
      tableRef.current?.scrollIntoView({ behavior: "auto", block: "start" });
    });
  }

  if (loadingDetail && !detail) {
    return (
      <>
        <PageHeader title="مراجعة الاستيراد" subtitle="جارٍ تحميل تفاصيل الكشف…" />
        <div className="fd-card fd-card-pad space-y-3">
          <div className="fd-skeleton h-8 w-56" />
          <div className="fd-skeleton h-24 w-full" />
          <div className="fd-skeleton h-24 w-full" />
        </div>
      </>
    );
  }

  if (error || !detail) {
    return (
      <>
        <PageHeader title="مراجعة الاستيراد" subtitle="مراجعة وتعديل الأسطر قبل التأكيد." />
        <div className="fd-card">
          <div className="px-6 py-12 text-center">
            <p role="alert" className="text-sm font-semibold text-[var(--fd-red-text)]">
              {error ?? "تعذر تحميل الاستيراد."}
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              <button type="button" className="fd-btn fd-btn-secondary h-11" onClick={refresh}>
                إعادة المحاولة
              </button>
              <Link href="/statements" className="fd-btn fd-btn-primary h-11">
                العودة إلى الكشوف
              </Link>
            </div>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <nav aria-label="مسار التصفح" className="mb-3 flex flex-wrap items-center gap-1.5 text-[11px] text-[var(--fd-ink-subtle)]">
        <Link href="/statements" className="hover:underline">
          كشوف الأقساط
        </Link>
        <span aria-hidden>/</span>
        <Link href={`/statements/${detail.id}`} className="max-w-[260px] truncate hover:underline">
          <bdi dir="ltr">{detail.source_filename}</bdi>
        </Link>
        <span aria-hidden>/</span>
        <span aria-current="page" className="text-[var(--fd-ink-muted)]">
          مراجعة
        </span>
      </nav>

      <PageHeader
        title="مراجعة الاستيراد"
        subtitle="راجع الأسطر، صحّح الأخطاء أو استثنِها، ثم أكّد الاستيراد."
        action={
          <div className="flex flex-wrap items-center gap-2">
            {reviewable && (
              <Link
                href={`/statements/upload?import=${detail.id}`}
                className="fd-btn fd-btn-secondary h-11"
              >
                تغيير مطابقة الأعمدة
              </Link>
            )}
            {sourceUrl && (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="fd-btn fd-btn-secondary h-11"
              >
                <ExternalLink size={15} aria-hidden />
                عرض الملف الأصلي
              </a>
            )}
            <Link href={`/statements/${detail.id}`} className="fd-btn fd-btn-secondary h-11">
              التفاصيل
            </Link>
          </div>
        }
      />

      <p className="mb-4 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
        <bdi dir="ltr">{detail.source_filename}</bdi>
        {detail.worksheet_name
          ? ` · ${detail.worksheet_name}`
          : detail.file_type === "pdf"
            ? " · ملف PDF"
            : ""}
        {` · الأسطر: ${formatNumber(totalRows)} · رُفع `}
        <bdi dir="ltr">
          {formatDateTime(detail.created_at, {
            locale: settings?.locale,
            timeZone: settings?.timezone,
          })}
        </bdi>
        {` بواسطة ${uploader}`}
      </p>

      {notice && (
        <p
          role="status"
          className="mb-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-green-soft)] px-3 py-2 text-[12px] text-[var(--fd-green-text)]"
        >
          {notice}
        </p>
      )}

      {confirmed && (
        <section className="mb-4 flex flex-wrap items-start gap-3 rounded-[var(--fd-radius-card)] border border-[var(--fd-green)] bg-[var(--fd-green-soft)] p-4">
          <CheckCircle2 size={20} className="mt-0.5 shrink-0 text-[var(--fd-green-text)]" aria-hidden />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-[var(--fd-green-text)]">
              تم تأكيد هذا الاستيراد. السجلات للعرض فقط.
            </p>
            <p className="mt-1 text-[12px] leading-6 text-[var(--fd-green-text)]">
              {detail.confirmed_at && (
                <>
                  تم التأكيد في{" "}
                  <bdi dir="ltr">
                    {formatDateTime(detail.confirmed_at, {
                      locale: settings?.locale,
                      timeZone: settings?.timezone,
                    })}
                  </bdi>
                  {detail.confirmed_by ? "، " : "."}
                </>
              )}
            </p>
          </div>
          <Link href={`/statements/${detail.id}`} className="fd-btn fd-btn-primary ms-auto h-11">
            عرض التفاصيل
          </Link>
        </section>
      )}

      {cancelled && (
        <section className="mb-4 flex flex-wrap items-center gap-3 rounded-[var(--fd-radius-card)] border border-[var(--fd-line)] bg-[var(--fd-surface-alt)] p-4">
          <p className="text-sm font-semibold text-[var(--fd-ink)]">
            أُلغي هذا الاستيراد. لم تُنشأ أي سجلات مالية.
          </p>
          <Link href="/statements" className="fd-btn fd-btn-secondary ms-auto h-11">
            العودة إلى الكشوف
          </Link>
        </section>
      )}

      {failed && (
        <section className="mb-4 rounded-[var(--fd-radius-card)] border border-[var(--fd-red)] bg-[var(--fd-red-soft)] p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-[var(--fd-red-text)]">
            <TriangleAlert size={17} aria-hidden />
            تعذر تحليل الملف
          </p>
          <p className="mt-1 text-[12px] leading-6 text-[var(--fd-red-text)]">
            {importErrorMessage(detail.error_summary) ?? "تعذر تحليل الملف."} لم تُنشأ أي
            سجلات مالية.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link href="/statements/upload" className="fd-btn fd-btn-primary h-11">
              رفع ملف آخر
            </Link>
            <Link href="/statements" className="fd-btn fd-btn-secondary h-11">
              العودة إلى الكشوف
            </Link>
          </div>
        </section>
      )}

      {processing && (
        <section className="fd-card fd-card-pad mb-4 flex items-center gap-3">
          <LoaderCircle size={18} className="animate-spin text-[var(--fd-brand)]" aria-hidden />
          <p className="text-[13px] text-[var(--fd-ink-muted)]">جارٍ تحليل الملف…</p>
        </section>
      )}

      {uploaded && (
        <section className="mb-4 flex flex-wrap items-center gap-3 rounded-[var(--fd-radius-card)] border border-[var(--fd-line)] bg-[var(--fd-surface-alt)] p-4">
          <p className="text-sm font-semibold text-[var(--fd-ink)]">
            لا توجد أسطر للمراجعة بعد. أكمل اختيار الورقة أولًا.
          </p>
          <Link
            href={`/statements/upload?import=${detail.id}`}
            className="fd-btn fd-btn-secondary ms-auto h-11"
          >
            اختيار الورقة
          </Link>
        </section>
      )}

      {showCounts && (
        <section className="fd-card mb-4 overflow-hidden" aria-labelledby="counts-title">
          <div className="border-b border-[var(--fd-line)] px-5 py-3">
            <h2 id="counts-title" className="text-[12px] font-semibold text-[var(--fd-ink)]">
              أعداد الأسطر
            </h2>
          </div>
          <div className="p-4">
            <ImportCounts
              total={totalRows}
              valid={
                warningRows !== null ? Math.max(validRows - warningRows, 0) : validRows
              }
              invalid={invalidRows}
              warnings={warningRows}
              excluded={excludedRows ?? undefined}
              showWarnings
              showDuplicates={false}
            />
            {(detail.warnings ?? []).length > 0 && (
              <IssueList issues={detail.warnings ?? []} className="mt-3" showCodes />
            )}
          </div>
        </section>
      )}

      {showTable && ambiguousIds.length > 0 && (
        <AmbiguousGuardianNotice
          ids={ambiguousIds}
          rows={ambiguousRows}
          onReveal={revealRow}
          onResolve={(row) => openGuardian(guardianByRow.get(row.row_id) ?? row)}
          onDismiss={() => {
            setAmbiguousIds([]);
            setAmbiguousRows([]);
            setConfirmAmbiguous(null);
          }}
        />
      )}

      {showTable && (
        <section
          className={`fd-card min-w-0 overflow-hidden ${reviewable ? "pb-32" : ""}`}
          aria-labelledby="rows-title"
          ref={tableRef}
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--fd-line)] px-5 py-4">
            <div className="flex min-w-0 items-center gap-2">
              <span
                className="h-4 w-1 shrink-0 rounded-full bg-[var(--fd-brand)]"
                aria-hidden
              />
              <div className="min-w-0">
                <h2 id="rows-title" className="text-sm font-semibold text-[var(--fd-ink)]">
                  أسطر الكشف
                </h2>
                {guardianLoading && !guardianData ? (
                  <p className="mt-0.5 text-[11px] text-[var(--fd-ink-subtle)]">
                    جارٍ التحقق من مطابقات أولياء الأمور…
                  </p>
                ) : guardianSummary.length > 0 ? (
                  <p className="mt-0.5 text-[11px] text-[var(--fd-ink-subtle)]">
                    مطابقة أولياء الأمور:{" "}
                    {guardianSummary.map((item, index) => (
                      <span key={item.key}>
                        {index > 0 && " · "}
                        {item.label}{" "}
                        <bdi className="tabular-nums">{formatNumber(item.count)}</bdi>
                      </span>
                    ))}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="flex flex-wrap items-end gap-2">
              <div>
                <label htmlFor="row-filter" className="fd-label mb-1 text-[11px]">
                  الحالة
                </label>
                <select
                  id="row-filter"
                  className="fd-input h-11 w-[140px]"
                  value={filter}
                  onChange={(event) =>
                    guardEditing(() => {
                      setFilter(event.target.value);
                      setPage(1);
                    })
                  }
                  disabled={editing}
                >
                  {FILTER_OPTIONS.map((option) => (
                    <option key={option.value || "all"} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <form
                className="flex items-end gap-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  guardEditing(() => {
                    setQuery(searchInput.trim());
                    setPage(1);
                  });
                }}
              >
                <div>
                  <label htmlFor="row-search" className="fd-label mb-1 text-[11px]">
                    بحث
                  </label>
                  <input
                    id="row-search"
                    className="fd-input h-11 w-[190px]"
                    value={searchInput}
                    onChange={(event) => setSearchInput(event.target.value)}
                    placeholder="ابحث باسم ولي الأمر أو رقم الهاتف"
                    disabled={editing}
                  />
                </div>
                <button
                  type="submit"
                  className="fd-btn fd-btn-secondary h-11 px-3"
                  aria-label="بحث"
                  disabled={editing}
                >
                  <Search size={15} aria-hidden />
                </button>
              </form>

              {(query || filter) && (
                <button
                  type="button"
                  className="fd-btn fd-btn-ghost h-11 px-3 text-[12px]"
                  onClick={() =>
                    guardEditing(() => {
                      setSearchInput("");
                      setQuery("");
                      setFilter("");
                      setPage(1);
                    })
                  }
                  disabled={editing}
                >
                  مسح عوامل التصفية
                </button>
              )}

              <button
                type="button"
                className="fd-btn fd-btn-ghost h-11 px-3"
                onClick={refresh}
                disabled={loadingRows || editing}
                aria-label="تحديث الأسطر"
                title="تحديث"
              >
                <RefreshCw size={15} aria-hidden />
              </button>
            </div>
          </div>

          {reviewable && (
            <BulkExclusionBar
              selectedCount={selected.size}
              pageCount={rows.length}
              invalidCount={invalidRows}
              busy={bulkBusy}
              disabled={selectionDisabled}
              onClear={clearSelection}
              onExcludeSelected={() => openBulk({ kind: "exclude", scope: "selected" })}
              onRestoreSelected={() => openBulk({ kind: "restore", scope: "selected" })}
              onExcludeInvalid={() => openBulk({ kind: "exclude", scope: "invalid" })}
            />
          )}

          {guardianError && (
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--fd-line)] bg-[var(--fd-amber-soft)] px-5 py-2 text-[11px] text-[var(--fd-amber-text)]">
              <span>تعذر تحميل مطابقات أولياء الأمور. {guardianError}</span>
              <button
                type="button"
                className="fd-btn fd-btn-secondary h-11 bg-[var(--fd-surface)] px-3 text-[11px]"
                onClick={() => setGuardianVersion((value) => value + 1)}
              >
                إعادة المحاولة
              </button>
            </div>
          )}

          {editing && (
            <p className="border-b border-[var(--fd-line)] bg-[var(--fd-amber-soft)] px-5 py-2 text-[11px] text-[var(--fd-amber-text)]">
              احفظ التعديل أو ألغِه قبل تغيير التصفية أو الصفحة.
            </p>
          )}

          {rowsError ? (
            <div role="alert" className="px-5 py-8 text-center">
              <p className="text-[13px] text-[var(--fd-red-text)]">{rowsError}</p>
              <button type="button" className="fd-btn fd-btn-secondary mt-4 h-11" onClick={refresh}>
                إعادة المحاولة
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto [contain:paint]">
              <table className="fd-table min-w-[1180px]" aria-busy={loadingRows}>
                <caption className="sr-only">أسطر كشف {detail.source_filename}</caption>
                <thead>
                  <tr>
                    {reviewable && (
                      <th scope="col" className="w-[52px]">
                        <label
                          className="flex h-11 w-11 cursor-pointer items-center justify-center"
                          title="تحديد كل الأسطر في هذه الصفحة"
                        >
                          <input
                            ref={selectAllRef}
                            type="checkbox"
                            className="h-5 w-5 accent-[var(--fd-brand)]"
                            checked={allSelected}
                            onChange={toggleAllRows}
                            disabled={selectionDisabled || rows.length === 0}
                            aria-label="تحديد كل الأسطر في هذه الصفحة"
                          />
                        </label>
                      </th>
                    )}
                    <th scope="col">ولي الأمر</th>
                    <th scope="col">الهاتف</th>
                    <th scope="col">الطالب</th>
                    <th scope="col">المتبقي</th>
                    <th scope="col">المدفوع</th>
                    <th scope="col" className="w-[82px]">العملة</th>
                    <th scope="col" className="min-w-[120px]">الحالة</th>
                    <th scope="col" className="w-[100px]">المصدر</th>
                    <th scope="col" className="w-[148px]">
                      <span className="sr-only">إجراءات السطر</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {loadingRows &&
                    Array.from({ length: 5 }).map((_, index) => (
                      <tr key={`skeleton-${index}`}>
                        <td colSpan={columnCount}>
                          <div className="fd-skeleton h-8 w-full" />
                        </td>
                      </tr>
                    ))}

                  {!loadingRows &&
                    rows.map((row) => {
                      const rowEdit = editingRowId === row.id;
                      const dirtyRow = rowEdit && dirty;
                      const saving = rowSaving === row.id;
                      const disabled = !reviewable || saving || (editing && !rowEdit);
                      const issues = row.validation_errors ?? [];
                      const issueId = `row-issues-${row.id}`;
                      const errorCount = issues.filter((issue) => issue.severity === "error").length;
                      const warningCount = issues.length - errorCount;
                      const phone = row.normalized_data.guardian_phone_normalized;
                      const phoneOriginal = row.normalized_data.guardian_phone_original;
                      const phoneLabel = issues
                        .map((issue) => issueLabel(issue.code))
                        .find((value) => Boolean(value));
                      const period = row.normalized_data.fee_period;
                      const remaining = originalValue(row, "remaining_balance");
                      const negative = remaining.trim().startsWith("-");
                      const guardianItem = reviewable
                        ? guardianByRow.get(row.id) ?? null
                        : null;
                      const isAmbiguous = guardianItem?.status === "ambiguous";
                      const marker =
                        row.validation_status === "invalid"
                          ? "border-s-[3px] border-s-[var(--fd-red)]"
                          : row.validation_status === "warning"
                            ? "border-s-[3px] border-s-[var(--fd-amber)]"
                            : isAmbiguous
                              ? "border-s-[3px] border-s-[var(--fd-amber)]"
                              : rowEdit
                                ? "border-s-[2px] border-s-[var(--fd-brand)]"
                                : "";
                      const rowTone = row.is_excluded
                        ? "bg-[var(--fd-surface-alt)]"
                        : row.validation_status === "invalid"
                          ? "bg-[var(--fd-red-soft)]"
                          : "";
                      return (
                        <Fragment key={row.id}>
                          <tr
                            id={`row-${row.id}`}
                            tabIndex={-1}
                            className={`scroll-mt-6 focus:bg-[var(--fd-brand-soft)] focus:outline-none ${rowTone}`}
                          >
                            {reviewable && (
                              <td className="align-top">
                                <label
                                  className="flex h-11 w-11 cursor-pointer items-center justify-center"
                                  title="تحديد السطر"
                                >
                                  <input
                                    type="checkbox"
                                    className="h-5 w-5 accent-[var(--fd-brand)]"
                                    checked={selected.has(row.id)}
                                    onChange={() => toggleRow(row.id)}
                                    disabled={selectionDisabled}
                                    aria-label={`تحديد السطر ${row.source_row_number ?? ""}${
                                      row.normalized_data.guardian_name
                                        ? ` — ${row.normalized_data.guardian_name}`
                                        : ""
                                    }`}
                                  />
                                </label>
                              </td>
                            )}
                            <th
                              scope="row"
                              className={`bg-transparent text-start align-top text-[13px] font-normal text-[var(--fd-ink)] ${marker}`}
                            >
                            {rowEdit ? (
                              <div>
                                <input
                                  className="fd-input h-10 text-[12px]"
                                  value={draft.guardian_name ?? originalValue(row, "guardian_name")}
                                  onChange={(event) =>
                                    updateDraft(row, "guardian_name", event.target.value)
                                  }
                                  onKeyDown={(event) => {
                                    if (event.key === "Escape") cancelEdit();
                                    if (event.key === "Enter") void saveRow(row);
                                  }}
                                  disabled={saving}
                                  aria-label={`اسم ولي الأمر للصف ${row.source_row_number ?? ""}`}
                                />
                                {draft.guardian_name !== undefined && (
                                  <OriginalLine value={originalValue(row, "guardian_name")} />
                                )}
                              </div>
                            ) : (
                              <div className="min-w-0">
                                <p className="truncate font-medium text-[var(--fd-ink)]">
                                  {bigid(row.normalized_data.guardian_name)}
                                </p>
                                {period && (
                                  <p className="mt-0.5 truncate text-[11px] text-[var(--fd-ink-subtle)]">
                                    الفصل: {period}
                                  </p>
                                )}
                                {isAmbiguous && guardianItem && (
                                  <p className="mt-1">
                                    <GuardianResolutionBadge item={guardianItem} />
                                  </p>
                                )}
                              </div>
                            )}
                            </th>

                          <td className="align-top whitespace-nowrap">
                            {rowEdit ? (
                              <div>
                                <input
                                  className="fd-input h-10 text-left text-[12px]"
                                  dir="ltr"
                                  inputMode="tel"
                                  value={
                                    draft.guardian_phone_original ??
                                    originalValue(row, "guardian_phone_original")
                                  }
                                  onChange={(event) =>
                                    updateDraft(row, "guardian_phone_original", event.target.value)
                                  }
                                  onKeyDown={(event) => {
                                    if (event.key === "Escape") cancelEdit();
                                    if (event.key === "Enter") void saveRow(row);
                                  }}
                                  disabled={saving}
                                  aria-label={`رقم الهاتف للصف ${row.source_row_number ?? ""}`}
                                />
                                {draft.guardian_phone_original !== undefined && (
                                  <OriginalLine
                                    value={
                                      phoneOriginal ??
                                      originalValue(row, "guardian_phone_original")
                                    }
                                  />
                                )}
                              </div>
                            ) : (
                              <>
                                <p className="text-[12px]">
                                  <bdi dir="ltr">{bigid(phone ?? phoneOriginal)}</bdi>
                                </p>
                                {phoneLabel && (
                                  <p className="mt-0.5 text-[10px] text-[var(--fd-amber-text)]">
                                    {phoneLabel}
                                  </p>
                                )}
                              </>
                            )}
                          </td>

                          <td className="align-top">
                            {rowEdit ? (
                              <div>
                                <input
                                  className="fd-input h-10 text-[12px]"
                                  value={draft.student_name ?? originalValue(row, "student_name")}
                                  onChange={(event) =>
                                    updateDraft(row, "student_name", event.target.value)
                                  }
                                  onKeyDown={(event) => {
                                    if (event.key === "Escape") cancelEdit();
                                    if (event.key === "Enter") void saveRow(row);
                                  }}
                                  disabled={saving}
                                  aria-label={`اسم الطالب للصف ${row.source_row_number ?? ""}`}
                                />
                                {draft.student_name !== undefined && (
                                  <OriginalLine value={originalValue(row, "student_name")} />
                                )}
                              </div>
                            ) : (
                              <span className="text-[12px]">
                                {bigid(row.normalized_data.student_name)}
                              </span>
                            )}
                          </td>

                          <td className="align-top whitespace-nowrap">
                            {rowEdit ? (
                              <div>
                                <input
                                  className="fd-input h-10 text-left text-[12px] tabular-nums"
                                  dir="ltr"
                                  inputMode="decimal"
                                  value={
                                    draft.remaining_balance ??
                                    originalValue(row, "remaining_balance")
                                  }
                                  onChange={(event) =>
                                    updateDraft(row, "remaining_balance", event.target.value)
                                  }
                                  onKeyDown={(event) => {
                                    if (event.key === "Escape") cancelEdit();
                                    if (event.key === "Enter") void saveRow(row);
                                  }}
                                  disabled={saving}
                                  aria-label={`المتبقي للصف ${row.source_row_number ?? ""}`}
                                />
                                {draft.remaining_balance !== undefined && (
                                  <OriginalLine
                                    money
                                    value={originalValue(row, "remaining_balance")}
                                  />
                                )}
                              </div>
                            ) : (
                              <span
                                className={`text-[12px] tabular-nums ${
                                  negative ? "text-[var(--fd-red-text)]" : ""
                                }`}
                              >
                                <bdi dir="ltr">{amountText(remaining)}</bdi>
                              </span>
                            )}
                          </td>

                          <td className="align-top whitespace-nowrap">
                            {rowEdit ? (
                              <div>
                                <input
                                  className="fd-input h-10 text-left text-[12px] tabular-nums"
                                  dir="ltr"
                                  inputMode="decimal"
                                  value={draft.amount_paid ?? originalValue(row, "amount_paid")}
                                  onChange={(event) =>
                                    updateDraft(row, "amount_paid", event.target.value)
                                  }
                                  onKeyDown={(event) => {
                                    if (event.key === "Escape") cancelEdit();
                                    if (event.key === "Enter") void saveRow(row);
                                  }}
                                  disabled={saving}
                                  aria-label={`المدفوع للصف ${row.source_row_number ?? ""}`}
                                />
                                {draft.amount_paid !== undefined && (
                                  <OriginalLine money value={originalValue(row, "amount_paid")} />
                                )}
                              </div>
                            ) : (
                              <span className="text-[12px] tabular-nums">
                                <bdi dir="ltr">
                                  {amountText(row.normalized_data.amount_paid)}
                                </bdi>
                              </span>
                            )}
                          </td>

                          <td className="align-top">
                            {rowEdit ? (
                              <div>
                                <input
                                  className="fd-input h-10 text-left text-[12px]"
                                  dir="ltr"
                                  maxLength={8}
                                  value={draft.currency ?? originalValue(row, "currency")}
                                  onChange={(event) =>
                                    updateDraft(row, "currency", event.target.value.toUpperCase())
                                  }
                                  onKeyDown={(event) => {
                                    if (event.key === "Escape") cancelEdit();
                                    if (event.key === "Enter") void saveRow(row);
                                  }}
                                  disabled={saving}
                                  aria-label={`العملة للصف ${row.source_row_number ?? ""}`}
                                />
                                {draft.currency !== undefined && (
                                  <OriginalLine value={originalValue(row, "currency")} />
                                )}
                              </div>
                            ) : (
                              <bdi dir="ltr" className="text-[11px] text-[var(--fd-ink-muted)]">
                                {bigid(row.normalized_data.currency)}
                              </bdi>
                            )}
                          </td>

                          <td className="align-top">
                            <StagedRowStatusPill status={row.validation_status} />
                            {issues.length > 0 && (
                              <p className="mt-0.5 text-[10px] text-[var(--fd-ink-subtle)]">
                                {errorCount > 0 && `الأخطاء: ${formatNumber(errorCount)}`}
                                {errorCount > 0 && warningCount > 0 && " · "}
                                {warningCount > 0 && `التحذيرات: ${formatNumber(warningCount)}`}
                              </p>
                            )}
                          </td>

                          <td className="align-top whitespace-nowrap text-[11px] text-[var(--fd-ink-muted)]">
                            {row.source_page_number != null
                              ? `صفحة ${row.source_page_number} · صف ${row.source_row_number ?? "—"}`
                              : `صف ${row.source_row_number ?? "—"}`}
                          </td>

                          <td className="align-top">
                            {reviewable ? (
                              <>
                            <div className="flex items-center gap-1">
                              {rowEdit ? (
                                <>
                                  <button
                                    type="button"
                                    className="fd-btn fd-btn-primary h-11 w-11 shrink-0 px-0"
                                    onClick={() => void saveRow(row)}
                                    disabled={!dirtyRow || saving}
                                    aria-label={`حفظ السجل ${row.normalized_data.guardian_name ?? ""}`}
                                    title="حفظ"
                                  >
                                    {saving ? (
                                      <LoaderCircle size={15} className="animate-spin" aria-hidden />
                                    ) : (
                                      <Save size={15} aria-hidden />
                                    )}
                                  </button>
                                  <button
                                    type="button"
                                    className="fd-btn fd-btn-secondary h-11 w-11 shrink-0 px-0"
                                    onClick={cancelEdit}
                                    disabled={saving}
                                    aria-label="إلغاء التعديل"
                                    title="إلغاء"
                                  >
                                    <X size={15} aria-hidden />
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    type="button"
                                    id={`edit-${row.id}`}
                                    className="fd-btn fd-btn-ghost h-11 w-11 shrink-0 px-0"
                                    onClick={() => beginEdit(row)}
                                    disabled={disabled}
                                    aria-label={`تعديل سجل ${row.normalized_data.guardian_name ?? ""}`}
                                    aria-describedby={issues.length > 0 ? issueId : undefined}
                                    title="تعديل"
                                  >
                                    <Pencil size={15} aria-hidden />
                                  </button>
                                  <button
                                    type="button"
                                    className="fd-btn fd-btn-ghost h-11 w-11 shrink-0 px-0"
                                    onClick={() => void toggleExclusion(row)}
                                    disabled={disabled}
                                    aria-pressed={row.is_excluded}
                                    aria-label={
                                      row.is_excluded
                                        ? `استعادة السجل ${row.normalized_data.guardian_name ?? ""}`
                                        : `استثناء السجل ${row.normalized_data.guardian_name ?? ""}`
                                    }
                                    aria-describedby={issues.length > 0 ? issueId : undefined}
                                    title={row.is_excluded ? "استعادة" : "استثناء"}
                                  >
                                    {row.is_excluded ? (
                                      <RotateCcw size={15} aria-hidden />
                                    ) : (
                                      <Ban size={15} aria-hidden />
                                    )}
                                  </button>
                                  {guardianItem && needsGuardianResolution(guardianItem) && (
                                    <button
                                      type="button"
                                      id={`guardian-${row.id}`}
                                      className="fd-btn fd-btn-ghost h-11 w-11 shrink-0 px-0"
                                      onClick={() => openGuardian(guardianItem)}
                                      disabled={disabled}
                                      aria-label={`تحديد ولي الأمر للسطر ${row.source_row_number ?? ""}`}
                                      aria-describedby={issues.length > 0 ? issueId : undefined}
                                      title="تحديد ولي الأمر"
                                    >
                                      <UserRoundSearch size={15} aria-hidden />
                                    </button>
                                  )}
                                </>
                              )}
                            </div>
                            {rowErrors[row.id] && (
                              <p
                                role="alert"
                                className="mt-1 max-w-[180px] text-[10px] leading-4 text-[var(--fd-red-text)]"
                              >
                                {rowErrors[row.id]}
                              </p>
                            )}
                              </>
                            ) : (
                              <span className="text-[11px] text-[var(--fd-ink-subtle)]">—</span>
                            )}
                          </td>
                          </tr>
                          {issues.length > 0 && (
                            <tr className={rowTone}>
                              <td colSpan={columnCount} className="border-t-0 p-0">
                                <RowIssues
                                  id={issueId}
                                  issues={issues}
                                  isExcluded={row.is_excluded}
                                />
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      );
                    })}

                  {!loadingRows && rows.length === 0 && (
                    <tr>
                      <td colSpan={columnCount} className="py-10 text-center text-[13px] text-[var(--fd-ink-muted)]">
                        {filter || query
                          ? "لا توجد أسطر مطابقة. جرّب حالة أخرى أو امسح البحث."
                          : "لم نستخرج أسطرًا من هذا الملف."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          <TablePager
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            onPage={(next) =>
              guardEditing(() => {
                setPage(next);
              })
            }
            busy={loadingRows || editing}
            itemLabel="سطر"
          />
        </section>
      )}

      {confirmed && (
        <p className="mt-4 text-[12px] text-[var(--fd-ink-subtle)]">
          تحتفظ هذه الصفحة بالعرض فقط بعد التأكيد. عدّلت الأسطر قبل التأكيد؟ راجع التفاصيل
          وسجل العمليات.
        </p>
      )}

      {reviewable && (
        <section
          className="sticky bottom-0 z-20 mt-5 rounded-t-[var(--fd-radius-card)] border border-[var(--fd-line)] bg-[var(--fd-surface)] p-4 shadow-[var(--fd-shadow-pop)]"
          aria-labelledby="confirm-bar-title"
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <h2 id="confirm-bar-title" className="sr-only">
                تأكيد الاستيراد
              </h2>
              <p className="text-[12px] font-medium text-[var(--fd-ink)]">
                للاستيراد {formatNumber(includedRows)}
                {excludedRows !== null && ` · مستثناة ${formatNumber(excludedRows)}`}
                {warningRows !== null &&
                  warningRows > 0 &&
                  ` · تحذيرات ${formatNumber(warningRows)}`}
              </p>

              <CurrencyTotals totals={detail.totals_by_currency} className="mt-1" />

              {hasWarnings && (
                <label className="mt-2 flex min-h-[44px] cursor-pointer items-start gap-2 text-[12px] leading-6 text-[var(--fd-amber-text)]">
                  <input
                    type="checkbox"
                    className="mt-1 h-5 w-5 shrink-0 accent-[var(--fd-brand)]"
                    checked={acknowledged}
                    onChange={(event) => setAcknowledged(event.target.checked)}
                    disabled={confirming}
                  />
                  راجعت التحذيرات وأفهم أن السجلات ستُستورد كما هي.
                </label>
              )}

              {blockedReason && (
                <p
                  id="confirm-block-reason"
                  role={blocking ? "alert" : undefined}
                  className={`mt-1 text-[12px] leading-6 ${
                    blocking ? "text-[var(--fd-red-text)]" : "text-[var(--fd-ink-muted)]"
                  }`}
                >
                  {blockedReason}
                  {blocking && (
                    <button
                      type="button"
                      className="fd-btn fd-btn-ghost ms-1 h-11 px-2 text-[12px] text-[var(--fd-red-text)] underline"
                      onClick={focusInvalid}
                    >
                      عرض الأخطاء
                    </button>
                  )}
                </p>
              )}
            </div>

            <div className="flex shrink-0 flex-col items-stretch gap-2">
              <button
                type="button"
                className="fd-btn fd-btn-primary h-11"
                onClick={() => {
                  setConfirmError(null);
                  setConfirmAmbiguous(null);
                  setConfirmOpen(true);
                }}
                disabled={!canConfirm}
                aria-describedby={blockedReason ? "confirm-block-reason" : undefined}
                aria-busy={confirming}
              >
                {confirming ? (
                  <LoaderCircle size={16} className="animate-spin" aria-hidden />
                ) : (
                  <CheckCircle2 size={16} aria-hidden />
                )}
                {confirming ? "جارٍ التأكيد…" : "تأكيد الاستيراد"}
              </button>
              <Link
                href="/statements"
                className="text-center text-[11px] text-[var(--fd-ink-muted)] hover:underline"
              >
                العودة إلى الكشوف
              </Link>
            </div>
          </div>
        </section>
      )}

      <Dialog
        open={confirmOpen}
        onClose={closeConfirmDialog}
        title="تأكيد الاستيراد"
        busy={confirming}
        description={
          <>
            سيتم إنشاء سجلات مالية من أسطر{" "}
            {detail.worksheet_name ? `«${detail.worksheet_name}»` : "هذا الملف"} في ملف{" "}
            <bdi dir="ltr">{detail.source_filename}</bdi>. لا يمكن التراجع عن التأكيد.
          </>
        }
      >
        <dl className="grid gap-2 text-[12px] sm:grid-cols-2">
          <div className="flex items-center justify-between gap-3">
            <dt className="text-[var(--fd-ink-muted)]">الأسطر</dt>
            <dd className="tabular-nums font-semibold text-[var(--fd-ink)]">
              {formatNumber(totalRows)}
            </dd>
          </div>
          <div className="flex items-center justify-between gap-3">
            <dt className="text-[var(--fd-ink-muted)]">للاستيراد</dt>
            <dd className="tabular-nums font-semibold text-[var(--fd-ink)]">
              {formatNumber(includedRows)}
            </dd>
          </div>
          {excludedRows !== null && (
            <div className="flex items-center justify-between gap-3">
              <dt className="text-[var(--fd-ink-muted)]">المستثناة</dt>
              <dd className="tabular-nums font-semibold text-[var(--fd-ink)]">
                {formatNumber(excludedRows)}
              </dd>
            </div>
          )}
          {warningRows !== null && warningRows > 0 && (
            <div className="flex items-center justify-between gap-3">
              <dt className="text-[var(--fd-ink-muted)]">التحذيرات</dt>
              <dd className="tabular-nums font-semibold text-[var(--fd-ink)]">
                {formatNumber(warningRows)}
              </dd>
            </div>
          )}
        </dl>

        <CurrencyTotals totals={detail.totals_by_currency} className="mt-3" />

        {(detail.warnings ?? []).length > 0 && (
          <div className="mt-3">
            <IssueList issues={detail.warnings ?? []} />
          </div>
        )}

        {hasWarnings && (
          <label className="mt-3 flex min-h-[44px] cursor-pointer items-start gap-2 rounded-[var(--fd-radius-control)] border border-[var(--fd-amber)] bg-[var(--fd-amber-soft)] p-3 text-[12px] leading-6 text-[var(--fd-amber-text)]">
            <input
              type="checkbox"
              className="mt-1 h-5 w-5 shrink-0 accent-[var(--fd-brand)]"
              checked={acknowledged}
              onChange={(event) => setAcknowledged(event.target.checked)}
              disabled={confirming}
            />
            راجعت التحذيرات وأفهم أن السجلات ستُستورد كما هي.
          </label>
        )}

        {confirmAmbiguous !== null && (
          <div
            role="alert"
            className="mt-3 rounded-[var(--fd-radius-control)] border border-[var(--fd-amber)] bg-[var(--fd-amber-soft)] p-3 text-[12px] leading-6 text-[var(--fd-amber-text)]"
          >
            <p className="flex items-start gap-2 font-semibold">
              <TriangleAlert size={16} className="mt-0.5 shrink-0" aria-hidden />
              لم يتم تأكيد الاستيراد.
            </p>
            <p className="mt-1">
              {confirmAmbiguous.length > 0
                ? `${rowsNeedResolution(confirmAmbiguous.length)} تحديد ولي الأمر قبل التأكيد.`
                : "يوجد سطر يحتاج تحديد ولي الأمر قبل التأكيد."}
            </p>
            <div className="mt-2">
              <button
                type="button"
                ref={ambiguousActionRef}
                className="fd-btn fd-btn-secondary h-11 bg-[var(--fd-surface)] px-3 text-[12px]"
                onClick={showAffectedRows}
              >
                عرض الأسطر المتأثرة
              </button>
            </div>
          </div>
        )}

        {confirmError && (
          <p role="alert" className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] text-[var(--fd-red-text)]">
            {confirmError}
          </p>
        )}

        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            className="fd-btn fd-btn-secondary h-11"
            onClick={closeConfirmDialog}
            disabled={confirming}
            data-autofocus
          >
            إلغاء
          </button>
          <button
            type="button"
            className="fd-btn fd-btn-primary h-11"
            onClick={() => void confirmImport()}
            disabled={!canConfirm || confirming}
          >
            {confirming ? "جارٍ التأكيد…" : "تأكيد وإنشاء السجلات"}
          </button>
        </div>
      </Dialog>

      <ConfirmDialog
        open={bulkAction !== null}
        title={bulkDialog?.title ?? ""}
        description={bulkDialog?.description ?? ""}
        confirmLabel={bulkDialog?.confirmLabel ?? ""}
        confirmTone={bulkDialog?.tone}
        busyLabel="جارٍ تحديث الأسطر…"
        busy={bulkBusy}
        error={bulkError}
        onConfirm={() => void runBulkAction()}
        onClose={() => {
          if (bulkBusy) return;
          setBulkAction(null);
          setBulkError(null);
        }}
      />

      {guardianTarget && (
        <GuardianResolutionDialog
          item={guardianTarget}
          saving={guardianSaving}
          error={guardianSaveError}
          onSave={(resolution) => void saveGuardianResolution(resolution)}
          onClose={() => {
            if (guardianSaving) return;
            setGuardianTarget(null);
            setGuardianSaveError(null);
          }}
        />
      )}
    </>
  );
}

function OriginalLine({ value, money = false }: { value: string; money?: boolean }) {
  const text = value.trim() === "" ? "—" : money ? formatDecimalString(value) : value;
  return (
    <p className="mt-1 truncate text-[10px] text-[var(--fd-ink-subtle)]">
      الأصل: <bdi dir="ltr">{text}</bdi>
    </p>
  );
}

export default function ReviewStatementPage() {
  return (
    <Protected active="/statements">
      <ReviewContent />
    </Protected>
  );
}
