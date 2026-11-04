import { StatusPill } from "@/components/StatusPill";
import type { StagedRowStatus } from "@/lib/api";

const LABELS: Record<StagedRowStatus, string> = {
  valid: "صالح",
  warning: "تحذير",
  invalid: "خطأ",
  excluded: "مستبعد",
};

const TONES: Record<StagedRowStatus, "neutral" | "amber" | "green" | "red"> = {
  valid: "green",
  warning: "amber",
  invalid: "red",
  excluded: "neutral",
};

export function StagedRowStatusPill({ status }: { status: StagedRowStatus }) {
  return <StatusPill tone={TONES[status] ?? "neutral"}>{LABELS[status] ?? status}</StatusPill>;
}
