"use client";

import { useState } from "react";
import {
  IMPORT_FIELD_LABELS,
  MAPPING_FIELDS,
  type ColumnMapping,
} from "@/lib/api";

const MANUAL = "__manual__";

/** Fields whose source header is mapped more than once. */
export function duplicateMappingFields(mapping: ColumnMapping): string[] {
  const counts = new Map<string, number>();
  Object.values(mapping).forEach((header) => {
    if (header) counts.set(header, (counts.get(header) ?? 0) + 1);
  });
  return Object.entries(mapping)
    .filter(([, header]) => Boolean(header) && (counts.get(header) ?? 0) > 1)
    .map(([field]) => field);
}

function requirement(field: string): { marker: string; label: string; tone: string } {
  if (field === "guardian_name" || field === "remaining_balance" || field === "currency") {
    return { marker: "*", label: "مطلوب", tone: "text-[var(--fd-red-text)]" };
  }
  if (field === "guardian_phone") {
    return { marker: "†", label: "للتذكير", tone: "text-[var(--fd-amber-text)]" };
  }
  return { marker: "—", label: "اختياري", tone: "text-[var(--fd-ink-subtle)]" };
}

export function MappingTable({
  headers,
  mapping,
  suggested,
  onChange,
  disabled = false,
}: {
  headers: string[];
  mapping: ColumnMapping;
  suggested?: ColumnMapping | null;
  onChange: (field: string, header: string) => void;
  disabled?: boolean;
}) {
  const [manualFields, setManualFields] = useState<Record<string, boolean>>({});
  const duplicates = duplicateMappingFields(mapping);

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="fd-table min-w-[620px]">
          <caption className="sr-only">
            مطابقة أعمدة الملف بالحقول المعتمدة. الحقول المعلّمة بـ * مطلوبة.
          </caption>
          <thead>
            <tr>
              <th scope="col">الحقل</th>
              <th scope="col">المتطلب</th>
              <th scope="col">عمود الملف</th>
              <th scope="col" className="w-[1%] whitespace-nowrap">
                الاقتراح
              </th>
            </tr>
          </thead>
          <tbody>
            {MAPPING_FIELDS.map((field) => {
              const selectId = `mapping-${field}`;
              const req = requirement(field);
              const isManual =
                (manualFields[field] && !mapping[field]) ||
                (Boolean(mapping[field]) && !headers.includes(mapping[field]));
              const selectValue = isManual ? MANUAL : mapping[field] ?? "";
              const isSuggested =
                Boolean(suggested?.[field]) && mapping[field] === suggested?.[field];
              const isDuplicate = duplicates.includes(field);
              const otherField = Object.entries(mapping).find(
                ([other, header]) =>
                  other !== field && Boolean(header) && header === mapping[field],
              )?.[0];
              return (
                <tr key={field}>
                  <td>
                    <label htmlFor={selectId} className="font-medium text-[var(--fd-ink)]">
                      {IMPORT_FIELD_LABELS[field]}
                    </label>
                  </td>
                  <td className="whitespace-nowrap text-[11px]">
                    <span className={`font-semibold ${req.tone}`}>{req.marker}</span>{" "}
                    <span className={req.tone}>{req.label}</span>
                  </td>
                  <td>
                    <select
                      id={selectId}
                      className={`fd-input h-11 w-full min-w-[180px] ${
                        isDuplicate ? "border-[var(--fd-red)]" : ""
                      }`}
                      value={selectValue}
                      onChange={(event) => {
                        const value = event.target.value;
                        if (value === MANUAL) {
                          setManualFields((current) => ({ ...current, [field]: true }));
                          onChange(field, "");
                        } else {
                          setManualFields((current) => ({ ...current, [field]: false }));
                          onChange(field, value);
                        }
                      }}
                      disabled={disabled || headers.length === 0}
                      aria-invalid={isDuplicate || undefined}
                      aria-describedby={isDuplicate ? `mapping-error-${field}` : undefined}
                    >
                      <option value="">لا شيء</option>
                      {headers.map((header) => (
                        <option key={header} value={header}>
                          {header}
                        </option>
                      ))}
                      <option value={MANUAL}>عمود غير مدرج…</option>
                    </select>

                    {isManual && (
                      <div className="mt-2">
                        <label
                          htmlFor={`mapping-manual-${field}`}
                          className="mb-1 block text-[11px] text-[var(--fd-ink-muted)]"
                        >
                          اسم العمود في الملف
                        </label>
                        <input
                          id={`mapping-manual-${field}`}
                          className="fd-input h-11 text-[12px]"
                          value={mapping[field] ?? ""}
                          onChange={(event) => onChange(field, event.target.value)}
                          placeholder="انسخ عنوان العمود كما يظهر في الملف."
                          disabled={disabled}
                          aria-invalid={isDuplicate || undefined}
                          aria-describedby={isDuplicate ? `mapping-error-${field}` : undefined}
                        />
                        <p className="mt-1 text-[10px] text-[var(--fd-ink-subtle)]">
                          انسخ عنوان العمود كما يظهر في الملف.
                        </p>
                      </div>
                    )}

                    {isDuplicate && (
                      <p
                        id={`mapping-error-${field}`}
                        role="alert"
                        className="mt-1 text-[11px] text-[var(--fd-red-text)]"
                      >
                        هذا العمود مستخدم بالفعل في «
                        {otherField ? IMPORT_FIELD_LABELS[otherField] ?? otherField : "حقل آخر"}
                        ».
                      </p>
                    )}
                  </td>
                  <td className="whitespace-nowrap">
                    {isSuggested ? (
                      <span className="fd-pill fd-pill-green">مطابقة تلقائية</span>
                    ) : mapping[field] ? (
                      <span className="fd-pill fd-pill-neutral">يدوي</span>
                    ) : (
                      <span className="text-[11px] text-[var(--fd-ink-subtle)]">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="border-t border-[var(--fd-line)] px-4 py-2.5 text-[11px] leading-5 text-[var(--fd-ink-muted)]">
        بدون رقم هاتف يبقى السجل المالي، لكنه لا يصلح لرسائل التذكير.
      </p>

      {headers.length === 0 && (
        <p className="border-t border-[var(--fd-line)] px-4 py-3 text-[12px] text-[var(--fd-ink-muted)]">
          لم تُقرأ أي أعمدة من الملف بعد. اختر ورقة العمل أولًا ثم أعد المحاولة.
        </p>
      )}
    </div>
  );
}
