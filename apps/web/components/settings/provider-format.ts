import { formatDecimalString, formatNumber } from "@/lib/api";
import type { MessagingChannel } from "@/lib/api";

/**
 * Display helpers for the messaging-provider panel.
 *
 * The backend owns every value here. Unknown values are rendered verbatim
 * instead of being guessed, so a new provider mode never gets a misleading
 * Arabic label.
 */

export const MESSAGING_CHANNELS: ReadonlyArray<{ value: MessagingChannel; label: string }> = [
  { value: "local_sms", label: "رسائل محلية (local_sms)" },
  { value: "sms", label: "رسائل SMS (sms)" },
];

export function isMessagingChannel(value: string | null | undefined): value is MessagingChannel {
  return value === "local_sms" || value === "sms";
}

export function channelLabel(channel: string | null | undefined): string {
  if (!channel) return "—";
  const match = MESSAGING_CHANNELS.find((item) => item.value === channel);
  return match ? match.label : channel;
}

const CREDENTIAL_SOURCE_LABELS: Record<string, string> = {
  env: "متغيرات البيئة",
  environment: "متغيرات البيئة",
  database: "قاعدة البيانات",
  db: "قاعدة البيانات",
  file: "ملف الإعدادات",
  vault: "خزنة الأسرار",
  secret_manager: "خزنة الأسرار",
  none: "لا يوجد",
};

export function credentialSourceLabel(source: string | null | undefined): string {
  if (!source) return "—";
  return CREDENTIAL_SOURCE_LABELS[source.toLowerCase()] ?? source;
}

const TEST_MODE_LABELS: Record<string, string> = {
  live: "إرسال فعلي",
  dry_run: "محاكاة (dry-run)",
  fake: "مزوّد وهمي",
  sandbox: "بيئة اختبار",
  allowlist: "قائمة سماح فقط",
};

export function testModeLabel(mode: string | null | undefined): string {
  if (!mode) return "غير محدد";
  return TEST_MODE_LABELS[mode.toLowerCase()] ?? mode;
}

/**
 * Fail safe: only an explicit "live" mode counts as real sending. Anything
 * else (unknown, dry_run, fake) is presented as a simulation.
 */
export function isDryRunMode(mode: string | null | undefined): boolean {
  return (mode ?? "").toLowerCase() !== "live";
}

const OUTCOME_SUCCESS = new Set([
  "success",
  "sent",
  "delivered",
  "accepted",
  "queued",
  "ok",
  "simulated",
  "dry_run",
]);

/** Not delivered, but not a hard failure either. */
const OUTCOME_WARNING = new Set(["duplicate"]);

const OUTCOME_FAILURE = new Set([
  "error",
  "failed",
  "failure",
  "rejected",
  "blocked",
  "invalid",
  "denied",
  "rate_limited",
  "timeout",
]);

export function outcomeTone(
  outcome: string | null | undefined,
): "green" | "red" | "amber" | "neutral" {
  const value = (outcome ?? "").toLowerCase();
  if (OUTCOME_SUCCESS.has(value)) return "green";
  if (OUTCOME_FAILURE.has(value)) return "red";
  if (OUTCOME_WARNING.has(value)) return "amber";
  return "neutral";
}

const OUTCOME_LABELS: Record<string, string> = {
  success: "نجاح",
  sent: "أُرسل",
  delivered: "تم التسليم",
  accepted: "قُبل",
  queued: "في قائمة المزوّد",
  duplicate: "مكرر",
  ok: "ناجح",
  simulated: "محاكاة ناجحة",
  dry_run: "محاكاة",
  error: "خطأ",
  failed: "فشل",
  failure: "فشل",
  rejected: "مرفوض",
  blocked: "محجوب",
  invalid: "غير صالح",
  denied: "مرفوض",
  rate_limited: "محدود المعدل",
  timeout: "غير معروف",
  unknown: "غير معروف",
};

export function outcomeLabel(outcome: string | null | undefined): string {
  if (!outcome) return "بدون نتيجة";
  return OUTCOME_LABELS[outcome.toLowerCase()] ?? outcome;
}

const PREFLIGHT_LABELS: Record<string, string> = {
  ok: "ناجح",
  success: "ناجح",
  sufficient: "الرصيد كافٍ",
  insufficient: "الرصيد غير كافٍ",
  blocked: "محجوب",
  unavailable: "غير متاح",
  dry_run: "محاكاة",
};

export function preflightLabel(preflight: boolean | string | null | undefined): string {
  if (typeof preflight === "boolean") return preflight ? "ناجح" : "لم ينجح";
  if (!preflight) return "—";
  return PREFLIGHT_LABELS[preflight.toLowerCase()] ?? preflight;
}

/** Money stays a string unless the API already returned a number. */
export function formatBalanceValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    return Number.isFinite(value) ? formatNumber(value) : "—";
  }
  const trimmed = value.trim();
  return trimmed ? formatDecimalString(trimmed) : "—";
}

/** Conservative E.164 check used before calling the test-send endpoint. */
export const E164_PATTERN = /^\+[1-9]\d{7,14}$/;

export function isE164(value: string): boolean {
  return E164_PATTERN.test(value.trim());
}
