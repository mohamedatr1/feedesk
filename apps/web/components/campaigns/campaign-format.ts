import { ApiError } from "@/lib/api";

type Tone = "neutral" | "green" | "amber" | "red";

export const CAMPAIGN_STATUS_META: Record<
  string,
  { label: string; tone: Tone; tabLabel: string; meaning: string }
> = {
  draft: {
    label: "مسودة",
    tone: "neutral",
    tabLabel: "مسودة",
    meaning: "لم تُرسل للاعتماد",
  },
  awaiting_approval: {
    label: "بانتظار الاعتماد",
    tone: "amber",
    tabLabel: "بانتظار الاعتماد",
    meaning: "بانتظار اعتماد مدير النظام",
  },
  approved: {
    label: "معتمدة",
    tone: "green",
    tabLabel: "معتمدة",
    meaning: "لم تبدأ معالجة الرسائل",
  },
  sending: {
    label: "قيد المعالجة",
    tone: "amber",
    tabLabel: "قيد المعالجة",
    meaning: "بدأت معالجة الرسائل ولم تنتهِ",
  },
  completed: {
    label: "اكتملت المعالجة",
    tone: "green",
    tabLabel: "اكتملت المعالجة",
    meaning: "انتهت معالجة كل الرسائل",
  },
  completed_with_errors: {
    label: "اكتملت مع أخطاء",
    tone: "amber",
    tabLabel: "اكتملت مع أخطاء",
    meaning: "انتهت المعالجة، وبعض الرسائل فشلت أو نتيجتها غير معروفة",
  },
  failed: {
    label: "فشلت المعالجة",
    tone: "red",
    tabLabel: "فشلت المعالجة",
    meaning: "فشلت كل محاولات الإرسال",
  },
  cancelled: {
    label: "ملغاة",
    tone: "neutral",
    tabLabel: "ملغاة",
    meaning: "أُلغيت الحملة",
  },
};

/** Campaigns whose messages have moved past the M3 "nothing sent" boundary. */
export const PROCESSING_CAMPAIGN_STATUSES = [
  "sending",
  "completed",
  "completed_with_errors",
  "failed",
] as const;

export function isProcessingCampaignStatus(status: string): boolean {
  return (PROCESSING_CAMPAIGN_STATUSES as readonly string[]).includes(status);
}

export function campaignStatusMeaning(status: string): string {
  return CAMPAIGN_STATUS_META[status]?.meaning ?? "—";
}

/**
 * M3 filter tabs and count probes. The four M4 derived statuses render in rows
 * and on the results page, but deliberately do not add tabs to the M3 layout.
 */
export const CAMPAIGN_STATUSES = [
  "draft",
  "awaiting_approval",
  "approved",
  "cancelled",
] as const;

export function campaignStatusLabel(status: string): string {
  return CAMPAIGN_STATUS_META[status]?.label ?? "—";
}

/** A short, truthful next step for an exclusion code. */
export function exclusionHint(code: string): string {
  switch (code) {
    case "ZERO_BALANCE":
      return "لا يوجد مبلغ متبقٍّ على هذا السجل.";
    case "NEGATIVE_BALANCE":
      return "يحتاج السجل إلى مراجعة مالية قبل التذكير.";
    case "MISSING_CURRENCY":
      return "صحّح العملة في كشف جديد مؤكد ثم أنشئ حملة.";
    case "MISSING_PHONE":
      return "أضف رقم ولي الأمر في كشف جديد مؤكد ثم أنشئ حملة.";
    case "INVALID_PHONE":
      return "صحّح الرقم بصيغة دولية تبدأ بـ +963 في كشف جديد مؤكد.";
    case "GUARDIAN_INACTIVE":
      return "أعد تفعيل الحساب قبل إنشاء حملة جديدة.";
    default:
      return "";
  }
}

/** The fix line shown next to a campaign-level blocking reason. */
export function blockingHint(code: string): string {
  switch (code) {
    case "NO_ELIGIBLE_RECIPIENTS":
      return "لا يوجد ولي أمر مؤهل في هذا الكشف. راجع السجلات المستثناة أدناه.";
    case "TEMPLATE_INACTIVE":
      return "القالب المستخدم لم يعد نشطًا.";
    case "TEMPLATE_NOT_FOUND":
      return "لم نجد القالب المستخدم في هذه الحملة.";
    case "UNRESOLVED_VARIABLES":
      return "قالب الرسالة يحتوي متغيرات غير معروفة.";
    default:
      return "";
  }
}

export function shortenHash(hash: string): string {
  if (hash.length <= 12) return hash;
  return `${hash.slice(0, 6)}…${hash.slice(-4)}`;
}

export function errorText(err: unknown, fallback: string): string {
  if (err instanceof ApiError && err.messageAr) return err.messageAr;
  if (err instanceof ApiError) return fallback;
  return fallback;
}

/**
 * A 409 from submit/approve/cancel means another session changed the
 * campaign. The UI refetches and asks the reader to look again.
 */
export function isStaleView(err: unknown): boolean {
  if (!(err instanceof ApiError)) return false;
  if (err.status === 409) return true;
  return ["CAMPAIGN_CHANGED", "REVISION_CONFLICT"].includes(err.code);
}

export const STALE_VIEW_MESSAGE =
  "تغيّرت الحملة منذ فتحها. حُدِّثت الصفحة؛ راجع البيانات ثم أعد المحاولة.";

export function isNoticeList(value: unknown): value is Array<{ code: string }> {
  return Array.isArray(value);
}
