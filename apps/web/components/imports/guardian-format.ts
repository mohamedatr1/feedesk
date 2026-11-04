import { formatNumber } from "@/lib/api";
import type { GuardianCandidateRow } from "@/lib/api";

export type GuardianTone = "neutral" | "amber" | "green" | "red";

type StatusMeta = {
  label: string;
  tone: GuardianTone;
  hint: string;
};

/**
 * Row-level matching states. An unknown status renders its raw value with a
 * neutral tone so a new backend state never inherits a wrong Arabic sentence.
 */
const STATUS_META: Record<string, StatusMeta> = {
  exact: {
    label: "تطابق تام",
    tone: "green",
    hint: "هناك مرشح واحد واضح لهذا السطر.",
  },
  same_name: {
    label: "اسم متطابق",
    tone: "amber",
    hint: "الاسم يطابق أكثر من سجل. راجع الهاتف أو اختر السجل الصحيح.",
  },
  shared_phone: {
    label: "هاتف مشترك",
    tone: "amber",
    hint: "الهاتف مسجل لأكثر من ولي أمر. اختر السجل الصحيح.",
  },
  ambiguous: {
    label: "ملتبس",
    tone: "amber",
    hint: "أكثر من مرشح محتمل، لذلك لا يتوفر الربط التلقائي. حدد ولي الأمر يدويًا.",
  },
  manual: {
    label: "تحديد يدوي",
    tone: "neutral",
    hint: "لا يوجد مرشح واضح. اربط ولي أمر موجودًا أو أنشئ سجلًا جديدًا.",
  },
};

export function guardianStatusMeta(status: string): StatusMeta {
  return (
    STATUS_META[status] ?? {
      label: status?.trim() ? status : "—",
      tone: "neutral",
      hint: "",
    }
  );
}

const MATCH_LABELS: Record<string, string> = {
  exact: "تطابق تام",
  name: "تطابق الاسم",
  phone: "تطابق الهاتف",
};

export function guardianMatchLabel(match: string): string {
  return MATCH_LABELS[match] ?? (match?.trim() ? match : "—");
}

const MATCH_TONES: Record<string, GuardianTone> = {
  exact: "green",
  name: "amber",
  phone: "amber",
};

export function guardianMatchTone(match: string): GuardianTone {
  return MATCH_TONES[match] ?? "neutral";
}

/**
 * The resolution action is only useful when the backend returned candidates
 * or the row is explicitly waiting for a manual decision.
 */
export function needsGuardianResolution(item: GuardianCandidateRow): boolean {
  return (
    (item.candidates ?? []).length > 0 ||
    item.mode === "manual" ||
    item.status === "manual" ||
    item.status === "ambiguous"
  );
}

/**
 * Arabic agreement for "N rows need …" sentences: "سطر واحد يحتاج",
 * "سطران يحتاجان", "3 أسطر تحتاج", "12 سطرًا يحتاج".
 */
export function rowsNeedResolution(count: number): string {
  if (count === 1) return "سطر واحد يحتاج";
  if (count === 2) return "سطران يحتاجان";
  const rule = new Intl.PluralRules("ar").select(count);
  if (rule === "few") return `${formatNumber(count)} أسطر تحتاج`;
  return `${formatNumber(count)} سطرًا يحتاج`;
}

/** A compact "N · label" summary for the counts the contract returns. */
export function guardianCountsSummary(counts: {
  ambiguous: number;
  same_name: number;
  shared_phone: number;
  manual: number;
}): Array<{ key: string; label: string; count: number }> {
  return [
    { key: "ambiguous", label: "ملتبس", count: counts.ambiguous },
    { key: "same_name", label: "اسم متطابق", count: counts.same_name },
    { key: "shared_phone", label: "هاتف مشترك", count: counts.shared_phone },
    { key: "manual", label: "تحديد يدوي", count: counts.manual },
  ].filter((item) => item.count > 0);
}
