import { LoaderCircle } from "lucide-react";
import { StatusPill } from "@/components/StatusPill";
import type { ImportStatus } from "@/lib/api";

const LABELS: Record<string, string> = {
  uploaded: "تم الرفع",
  processing: "قيد المعالجة",
  review_required: "بانتظار المراجعة",
  ready_to_confirm: "جاهز للتأكيد",
  confirmed: "مؤكد",
  failed: "فشل الاستيراد",
  cancelled: "ملغى",
};

type Tone = "neutral" | "amber" | "green" | "red";

function toneFor(status: string): Tone {
  switch (status) {
    case "review_required":
      return "amber";
    case "ready_to_confirm":
    case "confirmed":
      return "green";
    case "failed":
    case "cancelled":
      return "red";
    default:
      return "neutral";
  }
}

export function importStatusLabel(status: ImportStatus | string): string {
  return LABELS[status] ?? status;
}

export function ImportStatusPill({ status }: { status: ImportStatus | string }) {
  return (
    <StatusPill tone={toneFor(status)}>
      {status === "processing" && (
        <LoaderCircle size={12} className="animate-spin" aria-hidden />
      )}
      {importStatusLabel(status)}
    </StatusPill>
  );
}

export const IMPORT_STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "كل الحالات" },
  { value: "review_required", label: LABELS.review_required },
  { value: "ready_to_confirm", label: LABELS.ready_to_confirm },
  { value: "uploaded", label: LABELS.uploaded },
  { value: "processing", label: LABELS.processing },
  { value: "confirmed", label: LABELS.confirmed },
  { value: "failed", label: LABELS.failed },
  { value: "cancelled", label: LABELS.cancelled },
];
