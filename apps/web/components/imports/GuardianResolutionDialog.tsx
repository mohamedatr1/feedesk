"use client";

import { useId, useState } from "react";
import { Check, LoaderCircle, UserPlus, Users, Wand2 } from "lucide-react";
import { formatNumber, type GuardianCandidateRow, type GuardianResolution, type GuardianResolutionMode } from "@/lib/api";
import { Dialog } from "@/components/Dialog";
import { StatusPill } from "@/components/StatusPill";
import {
  guardianMatchLabel,
  guardianMatchTone,
  guardianStatusMeta,
} from "@/components/imports/guardian-format";

const MODE_ORDER: GuardianResolutionMode[] = ["auto", "link_existing", "create_new"];

const MODE_META: Record<
  GuardianResolutionMode,
  { label: string; description: string; icon: typeof Wand2 }
> = {
  auto: {
    label: "ربط تلقائي",
    description: "يختار الخادم ولي الأمر المطابق تلقائيًا.",
    icon: Wand2,
  },
  link_existing: {
    label: "ربط ولي أمر موجود",
    description: "اختر أحد السجلات المرشحة أدناه.",
    icon: Users,
  },
  create_new: {
    label: "إنشاء ولي أمر جديد",
    description: "إنشاء سجل جديد من بيانات هذا السطر.",
    icon: UserPlus,
  },
};

function initialMode(item: GuardianCandidateRow): GuardianResolutionMode {
  const hasCandidates = (item.candidates ?? []).length > 0;
  if (item.mode === "link_existing" && item.resolved_guardian_id) return "link_existing";
  if (item.mode === "create_new") return "create_new";
  if (item.status === "manual" || item.status === "ambiguous") {
    return hasCandidates ? "link_existing" : "create_new";
  }
  return hasCandidates ? "auto" : "create_new";
}

function initialCandidate(
  item: GuardianCandidateRow,
  mode: GuardianResolutionMode,
): string | null {
  if (mode !== "link_existing") return null;
  const candidates = item.candidates ?? [];
  const resolved = item.resolved_guardian_id;
  if (resolved && candidates.some((candidate) => candidate.guardian_id === resolved)) {
    return resolved;
  }
  return candidates[0]?.guardian_id ?? null;
}

/**
 * Manual guardian resolution. Mounted only for the target row, so form state
 * resets naturally between rows. Phones come from `guardian_phone_masked`;
 * the raw row phone never enters this dialog.
 */
export function GuardianResolutionDialog({
  item,
  saving,
  error,
  onSave,
  onClose,
}: {
  item: GuardianCandidateRow;
  saving: boolean;
  error: string | null;
  onSave: (resolution: GuardianResolution) => void;
  onClose: () => void;
}) {
  const startMode = initialMode(item);
  const [mode, setMode] = useState<GuardianResolutionMode>(startMode);
  const [candidateId, setCandidateId] = useState<string | null>(() =>
    initialCandidate(item, startMode),
  );

  const groupId = useId();
  const candidates = item.candidates ?? [];
  const statusMeta = guardianStatusMeta(item.status);
  const autoDisabled = item.status === "ambiguous";
  const linkDisabled = candidates.length === 0;
  const canSave = !saving && (mode !== "link_existing" || Boolean(candidateId));

  function chooseMode(next: GuardianResolutionMode) {
    if (saving) return;
    setMode(next);
    if (next === "link_existing" && !candidateId && candidates.length > 0) {
      setCandidateId(candidates[0].guardian_id);
    }
  }

  function submit() {
    if (!canSave) return;
    if (mode === "link_existing") {
      if (!candidateId) return;
      onSave({ mode, guardian_id: candidateId });
      return;
    }
    onSave({ mode });
  }

  return (
    <Dialog
      open
      onClose={saving ? () => undefined : onClose}
      title="تحديد ولي الأمر"
      busy={saving}
      description={
        <>
          ولي الأمر: <bdi dir="auto">{item.guardian_name || "—"}</bdi>
          {" · "}
          <bdi dir="ltr">{item.guardian_phone_masked || "—"}</bdi>
        </>
      }
    >
      <div className="rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] bg-[var(--fd-surface-alt)] p-3">
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill tone={statusMeta.tone}>{statusMeta.label}</StatusPill>
          {item.resolved_guardian_name && (
            <span className="text-[11px] text-[var(--fd-ink-muted)]">
              المحدد حاليًا: <bdi dir="auto">{item.resolved_guardian_name}</bdi>
            </span>
          )}
        </div>
        {statusMeta.hint && (
          <p className="mt-1.5 text-[12px] leading-6 text-[var(--fd-ink-muted)]">
            {statusMeta.hint}
          </p>
        )}
      </div>

      <fieldset className="mt-4">
        <legend className="fd-label">طريقة التحديد</legend>
        <div className="space-y-2">
          {MODE_ORDER.map((value) => {
            const meta = MODE_META[value];
            const Icon = meta.icon;
            const disabled =
              saving || (value === "auto" && autoDisabled) || (value === "link_existing" && linkDisabled);
            const selected = mode === value;
            return (
              <label
                key={value}
                className={`flex min-h-[44px] cursor-pointer items-start gap-3 rounded-[var(--fd-radius-control)] border p-3 transition ${
                  selected
                    ? "border-[var(--fd-brand)] bg-[var(--fd-brand-soft)]"
                    : "border-[var(--fd-line)] bg-[var(--fd-surface)]"
                } ${disabled ? "cursor-not-allowed opacity-60" : "hover:bg-[var(--fd-surface-alt)]"}`}
              >
                <input
                  type="radio"
                  name={`${groupId}-mode`}
                  value={value}
                  className="mt-1 h-4 w-4 shrink-0 accent-[var(--fd-brand)]"
                  checked={selected}
                  onChange={() => chooseMode(value)}
                  disabled={disabled}
                />
                <Icon
                  size={16}
                  className="mt-0.5 shrink-0 text-[var(--fd-ink-muted)]"
                  aria-hidden
                />
                <span className="min-w-0">
                  <span className="block text-[13px] font-medium text-[var(--fd-ink)]">
                    {meta.label}
                  </span>
                  <span className="mt-0.5 block text-[11px] leading-5 text-[var(--fd-ink-muted)]">
                    {value === "auto" && autoDisabled
                      ? "غير متاح: يوجد أكثر من مرشح محتمل."
                      : value === "link_existing" && linkDisabled
                        ? "لا يوجد مرشحون مطابقون لهذا السطر."
                        : meta.description}
                  </span>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {candidates.length > 0 && (
        <fieldset className="mt-4">
          <legend className="fd-label">
            السجلات المرشحة ({formatNumber(candidates.length)})
          </legend>
          <ul className="max-h-[300px] space-y-2 overflow-y-auto pe-1">
            {candidates.map((candidate) => {
              const selected = candidateId === candidate.guardian_id;
              const candidateStatus = guardianStatusMeta(candidate.status);
              const matchLabel = guardianMatchLabel(candidate.match);
              const showStatus = candidateStatus.label !== matchLabel;
              return (
                <li key={candidate.guardian_id}>
                  <label
                    className={`flex min-h-[44px] cursor-pointer items-start gap-3 rounded-[var(--fd-radius-control)] border p-3 transition ${
                      selected
                        ? "border-[var(--fd-brand)] bg-[var(--fd-brand-soft)]"
                        : "border-[var(--fd-line)] bg-[var(--fd-surface)]"
                    } ${saving ? "cursor-not-allowed opacity-60" : "hover:bg-[var(--fd-surface-alt)]"}`}
                  >
                    <input
                      type="radio"
                      name={`${groupId}-candidate`}
                      value={candidate.guardian_id}
                      className="mt-1 h-4 w-4 shrink-0 accent-[var(--fd-brand)]"
                      checked={selected}
                      onChange={() => {
                        setCandidateId(candidate.guardian_id);
                        setMode("link_existing");
                      }}
                      disabled={saving}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center justify-between gap-2">
                        <span className="min-w-0 truncate text-[13px] font-medium text-[var(--fd-ink)]">
                          <bdi dir="auto">{candidate.full_name || "—"}</bdi>
                        </span>
                        <StatusPill tone={guardianMatchTone(candidate.match)}>
                          {matchLabel}
                        </StatusPill>
                      </span>
                      <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-[var(--fd-ink-muted)]">
                        <bdi dir="ltr" className="whitespace-nowrap font-mono">
                          {candidate.phone_masked || "—"}
                        </bdi>
                        {showStatus && (
                          <>
                            <span aria-hidden>·</span>
                            <span>{candidateStatus.label}</span>
                          </>
                        )}
                      </span>
                      {item.resolved_guardian_id === candidate.guardian_id && (
                        <span className="mt-0.5 block text-[10px] font-medium text-[var(--fd-brand)]">
                          المحدد حاليًا
                        </span>
                      )}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </fieldset>
      )}

      {error && (
        <p
          role="alert"
          className="mt-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] text-[var(--fd-red-text)]"
        >
          {error}
        </p>
      )}

      <div className="mt-5 flex flex-wrap justify-end gap-2">
        <button
          type="button"
          className="fd-btn fd-btn-secondary h-11"
          onClick={onClose}
          disabled={saving}
          data-autofocus
        >
          إلغاء
        </button>
        <button
          type="button"
          className="fd-btn fd-btn-primary h-11"
          onClick={submit}
          disabled={!canSave}
          aria-busy={saving}
        >
          {saving ? (
            <LoaderCircle size={15} className="animate-spin" aria-hidden />
          ) : (
            <Check size={15} aria-hidden />
          )}
          {saving ? "جارٍ الحفظ…" : "حفظ تحديد ولي الأمر"}
        </button>
      </div>
    </Dialog>
  );
}
