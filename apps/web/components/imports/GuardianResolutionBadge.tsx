import { StatusPill } from "@/components/StatusPill";
import { guardianStatusMeta } from "@/components/imports/guardian-format";
import type { GuardianCandidateRow } from "@/lib/api";

/**
 * Compact row marker for the one state that blocks confirmation. The full
 * explanation lives in the row's dialog and the ambiguity notice.
 */
export function GuardianResolutionBadge({ item }: { item: GuardianCandidateRow }) {
  if (item.status !== "ambiguous") return null;
  const meta = guardianStatusMeta(item.status);

  return (
    <span className="inline-flex" title={meta.hint || undefined}>
      <StatusPill tone="amber">
        {meta.label}
        <span className="sr-only"> — اسم ولي الأمر يحتاج تحديدًا</span>
      </StatusPill>
    </span>
  );
}
