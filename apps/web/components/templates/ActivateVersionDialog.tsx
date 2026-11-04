"use client";

import { TriangleAlert } from "lucide-react";
import type { TemplateSummary } from "@/lib/api";
import { Dialog } from "@/components/Dialog";

export function ActivateVersionDialog({
  template,
  busy,
  error,
  onClose,
  onConfirm,
}: {
  template: TemplateSummary | null;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const open = template !== null;
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={template ? `تفعيل الإصدار ${template.version}` : "تفعيل الإصدار"}
      description={
        template
          ? `ستستخدم الحملات الجديدة هذا الإصدار من «${template.name}». الحملات المعتمدة لا تتغير.`
          : undefined
      }
      busy={busy}
    >
      {template && template.unknown_variables.length > 0 && (
        <p className="flex items-start gap-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-amber-soft)] p-3 text-[12px] leading-6 text-[var(--fd-amber-text)]">
          <TriangleAlert size={15} className="mt-1 shrink-0" aria-hidden />
          <span>هذا الإصدار يحتوي متغيرات غير معروفة، ولن تُعتمد الحملات التي تستخدمه.</span>
        </p>
      )}

      {error && (
        <p
          role="alert"
          className="mt-3 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] text-[var(--fd-red-text)]"
        >
          {error}
        </p>
      )}

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <button
          type="button"
          className="fd-btn fd-btn-secondary h-11"
          onClick={onClose}
          disabled={busy}
          data-autofocus
        >
          إلغاء
        </button>
        <button
          type="button"
          className="fd-btn fd-btn-primary h-11"
          onClick={onConfirm}
          disabled={busy || !template}
        >
          {busy ? "جارٍ التفعيل…" : "تفعيل"}
        </button>
      </div>
    </Dialog>
  );
}
