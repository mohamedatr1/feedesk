"use client";

import { Dialog } from "@/components/Dialog";

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  confirmTone = "danger",
  busyLabel = "جارٍ التنفيذ...",
  busy = false,
  error,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  description: React.ReactNode;
  confirmLabel: string;
  /** Restores and other non-destructive confirmations use `primary`. */
  confirmTone?: "danger" | "primary";
  busyLabel?: string;
  busy?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Dialog open={open} onClose={onClose} title={title} description={description} busy={busy}>
      {error && (
        <p
          role="alert"
          className="mb-4 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] text-[var(--fd-red-text)]"
        >
          {error}
        </p>
      )}
      <div className="flex flex-wrap justify-end gap-2">
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
          className={`fd-btn h-11 ${confirmTone === "primary" ? "fd-btn-primary" : "fd-btn-danger"}`}
          onClick={onConfirm}
          disabled={busy}
        >
          {busy ? busyLabel : confirmLabel}
        </button>
      </div>
    </Dialog>
  );
}
