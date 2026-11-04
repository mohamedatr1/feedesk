import { formatNumber } from "@/lib/api";
import type { DashboardTrendDelta, DashboardTrendPoint } from "@/lib/api";

/** Percent deltas are percentages, not fractions (8 → 8%). */
export function formatDelta(delta: number): string {
  const value = Math.round(Math.abs(delta) * 10) / 10;
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(value)}%`;
}

function numeric(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

/**
 * Read one currency's delta. Missing keys and null percentages mean "no
 * delta"; nothing is derived locally and no zero is substituted.
 */
export function currencyDelta(
  deltas: Record<string, DashboardTrendDelta> | null | undefined,
  currency: string,
): number | null {
  const pct = deltas?.[currency]?.pct;
  return typeof pct === "number" && Number.isFinite(pct) ? pct : null;
}

/**
 * Sparkline points for one currency, taken from each snapshot's
 * `totals_by_currency[currency]`. Amounts stay decimal strings everywhere else;
 * a numeric copy is made here only for plotting coordinates. Points are sorted
 * by date so the line always reads oldest → newest.
 */
export function currencySeries(
  series: DashboardTrendPoint[] | null | undefined,
  currency: string,
): number[] {
  if (!Array.isArray(series)) return [];

  const points: Array<{ date: string; value: number }> = [];
  for (const point of series) {
    const value = numeric(point?.totals_by_currency?.[currency]);
    if (value === null) continue;
    points.push({ date: typeof point.date === "string" ? point.date : "", value });
  }

  return points
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((point) => point.value);
}

/** Sorted, non-empty currency entries; decimal strings stay strings. */
export function currencyEntries(
  totals: Record<string, string> | null | undefined,
): Array<[string, string]> {
  return Object.entries(totals ?? {})
    .filter(([, amount]) => typeof amount === "string" && amount.trim() !== "")
    .sort(([a], [b]) => a.localeCompare(b));
}

/**
 * Show the configured symbol only for the configured default currency.
 * Any other currency keeps its API code; a symbol is never invented.
 */
export function currencyDisplay(
  currency: string,
  defaultCurrency: string | null | undefined,
  symbol: string | null | undefined,
): string {
  return currency === defaultCurrency && symbol ? symbol : currency;
}

export function daysPhrase(days: number): string {
  if (!Number.isFinite(days) || days <= 0) return "";
  if (days === 1) return "يوم واحد";
  if (days === 2) return "يومين";
  const rule = new Intl.PluralRules("ar").select(days);
  if (rule === "few") return `${formatNumber(days)} أيام`;
  return `${formatNumber(days)} يومًا`;
}

type NounForms = {
  zero: string;
  one: string;
  two: string;
  few: string;
  many: string;
  other: string;
};

const RECORD_NOUNS: NounForms = {
  zero: "لا سجلات",
  one: "سجل واحد",
  two: "سجلان",
  few: "سجلات",
  many: "سجل",
  other: "سجل",
};

const IMPORT_NOUNS: NounForms = {
  zero: "لا كشوف",
  one: "كشف واحد",
  two: "كشفان",
  few: "كشوف",
  many: "كشف",
  other: "كشف",
};

const CAMPAIGN_NOUNS: NounForms = {
  zero: "لا حملات",
  one: "حملة واحدة",
  two: "حملتان",
  few: "حملات",
  many: "حملة",
  other: "حملة",
};

/**
 * Arabic counted noun without diacritics: "7 سجلات", "31 كشف", "حملة واحدة".
 */
export function countPhrase(count: number, kind: "records" | "imports" | "campaigns"): string {
  const forms =
    kind === "records" ? RECORD_NOUNS : kind === "imports" ? IMPORT_NOUNS : CAMPAIGN_NOUNS;
  if (!Number.isFinite(count) || count <= 0) return forms.zero;
  if (count === 1) return forms.one;
  if (count === 2) return forms.two;
  const rule = new Intl.PluralRules("ar").select(count);
  if (rule === "few") return `${formatNumber(count)} ${forms.few}`;
  if (rule === "many") return `${formatNumber(count)} ${forms.many}`;
  return `${formatNumber(count)} ${forms.other}`;
}

/** Only same-origin app paths become links; anything else is inert text. */
export function safeInternalTarget(target: string | null | undefined): string | null {
  if (!target) return null;
  const value = target.trim();
  if (!value.startsWith("/") || value.startsWith("//")) return null;
  return value;
}

export type SeverityMeta = { label: string; tone: "neutral" | "amber" | "red" };

/**
 * Severity labels are deliberately vague on action: the backend owns the
 * meaning, and an unknown level gets no pill rather than an invented one.
 */
export function severityMeta(severity: string): SeverityMeta | null {
  switch ((severity ?? "").trim().toLowerCase()) {
    case "critical":
    case "error":
      return { label: "عاجل", tone: "red" };
    case "warning":
      return { label: "يحتاج متابعة", tone: "amber" };
    case "info":
    case "notice":
      return { label: "للمتابعة", tone: "neutral" };
    default:
      return null;
  }
}
