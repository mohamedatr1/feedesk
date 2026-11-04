import { formatNumber } from "@/lib/api";

export type OpsTone = "neutral" | "amber" | "green" | "red";

type JobStatusMeta = {
  label: string;
  tone: OpsTone;
  /** What the state means for the queue, in one short line. */
  meaning: string;
};

/**
 * Job statuses arrive as free strings from the queue backend. Known values get
 * a label; anything unrecognized is rendered verbatim with a neutral tone so a
 * new backend state never inherits a misleading Arabic word.
 */
export const JOB_STATUS_META: Record<string, JobStatusMeta> = {
  pending: {
    label: "بانتظار المعالجة",
    tone: "neutral",
    meaning: "لم يبدأ تنفيذ المهمة بعد.",
  },
  claimed: {
    label: "قيد المعالجة الآن",
    tone: "amber",
    meaning: "التقطها عامل تنفيذ ولم تنتهِ بعد.",
  },
  retry: {
    label: "بانتظار إعادة محاولة",
    tone: "amber",
    meaning: "جدول الخادم محاولة أخرى لهذه المهمة.",
  },
  done: {
    label: "انتهت المعالجة",
    tone: "green",
    meaning: "اكتملت المهمة.",
  },
  succeeded: {
    label: "انتهت المعالجة",
    tone: "green",
    meaning: "اكتملت المهمة.",
  },
  failed: {
    label: "فشلت المعالجة",
    tone: "red",
    meaning: "استنفدت المهمة محاولاتها.",
  },
  cancelled: {
    label: "ملغاة",
    tone: "neutral",
    meaning: "أُلغيت مع الحملة.",
  },
};

export function jobStatusLabel(status: string): string {
  return JOB_STATUS_META[status]?.label ?? status;
}

export function jobStatusTone(status: string): OpsTone {
  return JOB_STATUS_META[status]?.tone ?? "neutral";
}

/** Arabic counted noun for attempt counts, same rule set as messageNoun. */
export function attemptsLabel(count: number): string {
  if (!Number.isFinite(count) || count <= 0) return "بدون محاولات";
  const rule = new Intl.PluralRules("ar").select(count);
  switch (rule) {
    case "one":
      return "محاولة واحدة";
    case "two":
      return "محاولتان";
    case "few":
      return `${formatNumber(count)} محاولات`;
    default:
      return `${formatNumber(count)} محاولة`;
  }
}

/**
 * Compare a server timestamp with the summary's `generated_at`. No ticking
 * clock: the console describes the moment the snapshot was produced.
 */
export function isPast(
  value: string | null | undefined,
  nowIso: string | null | undefined,
): boolean {
  if (!value || !nowIso) return false;
  const time = Date.parse(value);
  const now = Date.parse(nowIso);
  return Number.isFinite(time) && Number.isFinite(now) && time < now;
}

/** A short last-error cell: summary first, then the raw message, then the code. */
export function jobErrorText(job: {
  last_error_summary: string | null;
  last_error: string | null;
  last_error_code: string | null;
}): string | null {
  const summary = job.last_error_summary?.trim();
  if (summary) return summary;
  const raw = job.last_error?.trim();
  if (raw) return raw;
  return job.last_error_code?.trim() || null;
}

export function lastPage(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(total / Math.max(pageSize, 1)));
}
