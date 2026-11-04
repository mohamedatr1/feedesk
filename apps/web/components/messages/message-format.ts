import { formatDecimalString, formatDateTime, type MessageSummary } from "@/lib/api";

export type MessageTone = "neutral" | "amber" | "green" | "red";

export type MessageStatusMeta = {
  label: string;
  tone: MessageTone;
  /** List / table second line when nothing more specific is known. */
  secondLine: string;
  filterLabel: string;
};

/**
 * The only user-facing message vocabulary (design spec §2.1). Every label in
 * the product is birthed here; components never type an Arabic status.
 */
export const MESSAGE_STATUS_META: Record<string, MessageStatusMeta> = {
  pending: {
    label: "بانتظار الإرسال",
    tone: "neutral",
    secondLine: "لم تُرسل بعد",
    filterLabel: "بانتظار الإرسال",
  },
  submitting: {
    label: "قيد الإرسال إلى المزوّد",
    tone: "amber",
    secondLine: "بانتظار رد المزوّد",
    filterLabel: "قيد الإرسال",
  },
  provider_accepted: {
    label: "قبلها المزوّد",
    tone: "amber",
    secondLine: "لم يصل تأكيد التسليم",
    filterLabel: "قبلها المزوّد",
  },
  queued_by_provider: {
    label: "في طابور المزوّد",
    tone: "amber",
    secondLine: "لم يصل تأكيد التسليم",
    filterLabel: "في طابور المزوّد",
  },
  delivered: {
    label: "تم التسليم",
    tone: "green",
    secondLine: "تم التسليم",
    filterLabel: "تم التسليم",
  },
  failed: {
    label: "فشل الإرسال",
    tone: "red",
    secondLine: "فشلت المحاولة",
    filterLabel: "فشل الإرسال",
  },
  unknown: {
    label: "نتيجة غير معروفة",
    tone: "amber",
    secondLine: "لا نعرف هل وصلت",
    filterLabel: "نتيجة غير معروفة",
  },
  cancelled: {
    label: "ملغاة",
    tone: "neutral",
    secondLine: "أُلغيت قبل المعالجة",
    filterLabel: "ملغاة",
  },
};

export function messageStatusMeta(status: string): MessageStatusMeta | null {
  return MESSAGE_STATUS_META[status] ?? null;
}

export function messageStatusLabel(status: string): string {
  return MESSAGE_STATUS_META[status]?.label ?? "—";
}

export const MESSAGE_FILTER_GROUPS: Array<{ label: string; statuses: string[] }> = [
  {
    label: "لم تنتهِ",
    statuses: ["pending", "submitting", "provider_accepted", "queued_by_provider"],
  },
  {
    label: "انتهت",
    statuses: ["delivered", "failed", "unknown", "cancelled"],
  },
];

/** `unknown` is a first-class state: amber, never red. */
export function messageSecondLine(
  message: Pick<
    MessageSummary,
    "internal_status" | "delivered_at" | "last_error_summary" | "next_attempt_at"
  >,
  formatted: (value: string | null) => string,
): string {
  const meta = MESSAGE_STATUS_META[message.internal_status];

  if (
    message.next_attempt_at &&
    (message.internal_status === "pending" || message.internal_status === "submitting") &&
    new Date(message.next_attempt_at).getTime() > Date.now()
  ) {
    return `إعادة محاولة ${formatted(message.next_attempt_at)}`;
  }

  if (message.internal_status === "delivered") {
    // An explicit delivery state with no timestamp: never invent one.
    return message.delivered_at
      ? `سُلّمت ${formatted(message.delivered_at)}`
      : "تم التسليم";
  }

  if (message.internal_status === "failed") {
    return message.last_error_summary?.trim() || "فشلت المحاولة";
  }

  return meta?.secondLine ?? "—";
}

/** The single explainer line for a message detail page (§2.1). */
export function messageStatusExplainer(
  message: Pick<
    MessageSummary,
    "internal_status" | "delivered_at" | "last_error_summary"
  >,
  formatted: (value: string | null) => string,
): string {
  switch (message.internal_status) {
    case "pending":
      return "لم تُرسل إلى المزوّد بعد. تُعالَج الرسائل بالترتيب.";
    case "submitting":
      return "جرت محاولة إرسال ولم يصل ردّها بعد.";
    case "provider_accepted":
      return "قبول المزوّد ليس تسليمًا. لا يصل تحديث تلقائي لحالة التسليم في هذه المرحلة.";
    case "queued_by_provider":
      return "وضع المزوّد الرسالة في طابوره. هذا لا يعني التسليم.";
    case "delivered":
      return message.delivered_at
        ? `وصل تأكيد تسليم من المزوّد في ${formatted(message.delivered_at)}.`
        : "وصل تأكيد تسليم من المزوّد.";
    case "failed": {
      const summary = message.last_error_summary?.trim();
      return summary
        ? `لم يقبل المزوّد الرسالة. ${summary} لا تُعاد تلقائيًا.`
        : "لم يقبل المزوّد الرسالة. لا تُعاد تلقائيًا.";
    }
    case "unknown":
      return "انتهت المحاولة دون رد واضح. قد تكون الرسالة وصلت، لذلك لا تُعاد تلقائيًا.";
    case "cancelled":
      return "أُلغيت مع إلغاء الحملة. لم تُرسل.";
    default:
      return "";
  }
}

export const TONE_BORDER: Record<MessageTone, string> = {
  neutral: "border-s-[var(--fd-line-strong)]",
  amber: "border-s-[var(--fd-amber)]",
  green: "border-s-[var(--fd-green)]",
  red: "border-s-[var(--fd-red)]",
};

export const TONE_TEXT: Record<MessageTone, string> = {
  neutral: "text-[var(--fd-ink-muted)]",
  amber: "text-[var(--fd-amber-text)]",
  green: "text-[var(--fd-green-text)]",
  red: "text-[var(--fd-red-text)]",
};

export function isTerminalMessageStatus(status: string): boolean {
  return ["provider_accepted", "queued_by_provider", "delivered", "failed", "unknown", "cancelled"].includes(
    status,
  );
}

export function formatMessageMoney(
  amount: string | null | undefined,
  currency: string | null | undefined,
): string {
  if (!amount || !currency) return "—";
  return `${currency} ${formatDecimalString(amount)}`;
}

export function middleTruncate(value: string, head = 8, tail = 2): string {
  if (value.length <= head + tail + 1) return value;
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}

/** Arabic counted noun for the few places a count needs one (§9.5). */
export function messageNoun(count: number): string {
  const rule = new Intl.PluralRules("ar").select(count);
  switch (rule) {
    case "zero":
      return "لا رسائل";
    case "one":
      return "رسالة واحدة";
    case "two":
      return "رسالتان";
    case "few":
      return "رسائل";
    default:
      return "رسالة";
  }
}

export function sumKnownCounts(
  counts: Partial<Record<string, number>> | null | undefined,
  statuses: string[],
): number | null {
  if (!counts) return null;
  let total = 0;
  for (const status of statuses) {
    const value = counts[status];
    if (typeof value !== "number") return null;
    total += value;
  }
  return total;
}

/** URL for the history list; filters and page are always URL-backed. */
export function messagesHref(params: {
  campaign_id?: string | null;
  status?: string | null;
  q?: string | null;
  page?: number | null;
}): string {
  const search = new URLSearchParams();
  if (params.campaign_id) search.set("campaign_id", params.campaign_id);
  if (params.status) search.set("status", params.status);
  if (params.q?.trim()) search.set("q", params.q.trim());
  if (params.page && params.page > 1) search.set("page", String(params.page));
  const query = search.toString();
  return query ? `/messages?${query}` : "/messages";
}

/** Default formatter for server timestamps (settings-aware at call sites). */
export function defaultDateFormatter(locale?: string | null, timeZone?: string | null) {
  return (value: string | null) =>
    value ? formatDateTime(value, { locale, timeZone }) : "—";
}
