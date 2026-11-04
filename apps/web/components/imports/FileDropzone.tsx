"use client";

import { useId, useRef, useState } from "react";
import { FileSpreadsheet, FileText, Upload, X } from "lucide-react";

const ALLOWED_EXTENSIONS = [".xlsx", ".pdf"];

export function fileExtension(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot).toLowerCase() : "";
}

export function validateImportFile(
  file: File,
  maxUploadMb?: number | null,
): string | null {
  const ext = fileExtension(file.name);
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return "هذا النوع غير مدعوم. المسموح: Excel (.xlsx) أو PDF.";
  }
  if (file.size === 0) {
    return "الملف فارغ. اختر ملفًا يحتوي على بيانات.";
  }
  if (maxUploadMb != null && maxUploadMb > 0 && file.size > maxUploadMb * 1024 * 1024) {
    return `حجم الملف أكبر من الحد المسموح (${maxUploadMb} ميغابايت).`;
  }
  return null;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} بايت`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} ك.ب`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} م.ب`;
}

export function FileDropzone({
  file,
  onFile,
  onClear,
  disabled = false,
  error,
  maxUploadMb,
}: {
  file: File | null;
  onFile: (file: File) => void;
  onClear: () => void;
  disabled?: boolean;
  error?: string | null;
  maxUploadMb?: number | null;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const helpId = useId();
  const errorId = useId();
  const shownError = error ?? localError;

  function pick(next: File | null | undefined) {
    if (!next || disabled) return;
    setLocalError(null);
    onFile(next);
  }

  return (
    <div>
      <div
        onDragOver={(event) => {
          if (disabled) return;
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          if (disabled) return;
          event.preventDefault();
          setDragging(false);
          if (event.dataTransfer.files.length > 1) {
            pick(event.dataTransfer.files?.[0]);
            setLocalError("ارفع ملفًا واحدًا في كل مرة.");
          } else {
            pick(event.dataTransfer.files?.[0]);
          }
        }}
        className={`rounded-[var(--fd-radius-card)] border-2 border-dashed p-6 text-center transition ${
          dragging
            ? "border-[var(--fd-brand)] bg-[var(--fd-brand-soft)]"
            : shownError
              ? "border-[var(--fd-red)] bg-[var(--fd-surface-alt)]"
              : "border-[var(--fd-line-strong)] bg-[var(--fd-surface-alt)]"
        } ${disabled ? "opacity-60" : ""}`}
      >
        <span className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--fd-surface)] text-[var(--fd-brand)]">
          <Upload size={22} strokeWidth={1.7} aria-hidden />
        </span>

        {file ? (
          <div className="space-y-2">
            <p className="flex flex-wrap items-center justify-center gap-2 text-sm font-semibold text-[var(--fd-ink)]">
              {fileExtension(file.name) === ".xlsx" ? (
                <FileSpreadsheet size={17} aria-hidden />
              ) : (
                <FileText size={17} aria-hidden />
              )}
              <bdi dir="ltr">{file.name}</bdi>
            </p>
            <p className="text-[12px] text-[var(--fd-ink-muted)]">
              {formatFileSize(file.size)} · {fileExtension(file.name).replace(".", "").toUpperCase()}
            </p>
            <button
              type="button"
              className="fd-btn fd-btn-secondary h-11"
              onClick={onClear}
              disabled={disabled}
            >
              <X size={15} aria-hidden />
              إزالة الملف
            </button>
          </div>
        ) : (
          <>
            <p className="text-sm font-semibold text-[var(--fd-ink)]">
              أسقط ملف الكشف هنا أو اختره من جهازك
            </p>
            <p id={helpId} className="mx-auto mt-1 max-w-md text-[12px] leading-6 text-[var(--fd-ink-muted)]">
              Excel (.xlsx) أو PDF
              {maxUploadMb != null && maxUploadMb > 0
                ? ` · حتى ${maxUploadMb} ميغابايت`
                : ""}
            </p>
            <button
              type="button"
              className="fd-btn fd-btn-primary mt-4 h-11"
              onClick={() => inputRef.current?.click()}
              disabled={disabled}
            >
              <Upload size={16} aria-hidden />
              اختيار ملف
            </button>
          </>
        )}

        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED_EXTENSIONS.join(",")}
          className="sr-only"
          disabled={disabled}
          aria-label="اختيار ملف الكشف"
          aria-describedby={shownError ? `${helpId} ${errorId}` : helpId}
          onChange={(event) => {
            pick(event.target.files?.[0]);
            // Allow re-selecting the same file after a validation error.
            event.target.value = "";
          }}
        />
      </div>

      {shownError && (
        <p
          id={errorId}
          role="alert"
          className="mt-2 rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] text-[var(--fd-red-text)]"
        >
          {shownError}
        </p>
      )}
    </div>
  );
}
