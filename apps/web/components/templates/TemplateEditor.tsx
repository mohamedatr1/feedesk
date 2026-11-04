"use client";

import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { Check, Minus, Save, TriangleAlert } from "lucide-react";
import type { TemplateDetail, TemplateVariable } from "@/lib/api";
import { formatNumber } from "@/lib/api";
import { TemplateBody } from "@/components/templates/TemplateBody";
import { VariablePalette } from "@/components/templates/VariablePalette";

function findVariables(body: string): string[] {
  const found = new Set<string>();
  const pattern = /\{\{\s*([A-Za-z0-9_]+)\s*\}\}/g;
  let match = pattern.exec(body);
  while (match) {
    found.add(match[1]);
    match = pattern.exec(body);
  }
  return [...found];
}

export function TemplateEditor({
  fromTemplate,
  nextVersion,
  variables,
  variablesError,
  saving,
  error,
  onSave,
}: {
  fromTemplate: TemplateDetail | null;
  nextVersion: number | null;
  variables: TemplateVariable[];
  variablesError: string | null;
  saving: boolean;
  error: string | null;
  onSave: (payload: { name: string; body: string }) => void;
}) {
  const [name, setName] = useState(fromTemplate?.name ?? "");
  const [body, setBody] = useState(fromTemplate?.template_body ?? "");
  const [nameError, setNameError] = useState<string | null>(null);
  const [bodyError, setBodyError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const nameLocked = fromTemplate !== null;

  const allowed = useMemo(
    () => new Set(variables.map((variable) => variable.name)),
    [variables],
  );
  const usedVariables = findVariables(body);
  const unknownVariables =
    variables.length > 0 ? usedVariables.filter((name) => !allowed.has(name)) : [];

  function insertVariable(variableName: string) {
    const textarea = textareaRef.current;
    const token = `{{${variableName}}}`;
    if (!textarea) {
      setBody((current) => `${current}${token}`);
      return;
    }
    const start = textarea.selectionStart ?? body.length;
    const end = textarea.selectionEnd ?? body.length;
    const next = `${body.slice(0, start)}${token}${body.slice(end)}`;
    setBody(next);
    setAnnouncement(`أُضيف المتغير {{${variableName}}}.`);
    requestAnimationFrame(() => {
      const element = textareaRef.current;
      if (!element) return;
      element.focus();
      const caret = start + token.length;
      element.setSelectionRange(caret, caret);
    });
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = name.trim();
    const trimmedBody = body.trim();
    let invalid = false;
    if (!trimmedName) {
      setNameError("أدخل اسم القالب.");
      invalid = true;
    } else {
      setNameError(null);
    }
    if (!trimmedBody) {
      setBodyError("أدخل نص الرسالة.");
      invalid = true;
    } else {
      setBodyError(null);
    }
    if (invalid) return;
    onSave({ name: trimmedName, body: trimmedBody });
  }

  return (
    <form onSubmit={submit} aria-busy={saving}>
      <div className="grid gap-5 xl:grid-cols-[1.4fr_0.9fr]">
        <div className="fd-card fd-card-pad space-y-5">
          <div>
            <label htmlFor="template-name" className="fd-label">
              اسم القالب
            </label>
            {nameLocked ? (
              <>
                <p className="min-h-11 rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] px-3 py-2 text-sm text-[var(--fd-ink)]">
                  <bdi dir="auto">{name}</bdi>
                </p>
                <p className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">
                  الاسم مثبّت لإنشاء إصدار من نفس القالب.
                </p>
              </>
            ) : (
              <>
                <input
                  id="template-name"
                  className="fd-input h-11"
                  maxLength={120}
                  value={name}
                  onChange={(event) => {
                    setName(event.target.value);
                    setNameError(null);
                  }}
                  disabled={saving}
                  aria-invalid={nameError ? true : undefined}
                  aria-describedby={nameError ? "template-name-error" : undefined}
                  required
                />
                {nameError && (
                  <p
                    id="template-name-error"
                    role="alert"
                    className="mt-1 text-[11px] text-[var(--fd-red-text)]"
                  >
                    {nameError}
                  </p>
                )}
                <p className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">
                  يُنشئ الحفظ إصدارًا جديدًا من نفس الاسم.
                </p>
              </>
            )}
          </div>

          <div>
            <label htmlFor="template-body" className="fd-label">
              نص الرسالة
            </label>
            <textarea
              id="template-body"
              ref={textareaRef}
              className="fd-input min-h-[320px] py-3 text-[15px] leading-[1.9]"
              value={body}
              onChange={(event) => {
                setBody(event.target.value);
                setBodyError(null);
              }}
              dir="rtl"
              lang="ar"
              spellCheck={false}
              disabled={saving}
              aria-invalid={bodyError ? true : undefined}
              aria-describedby={bodyError ? "template-body-error" : undefined}
            />
            {bodyError && (
              <p
                id="template-body-error"
                role="alert"
                className="mt-1 text-[11px] text-[var(--fd-red-text)]"
              >
                {bodyError}
              </p>
            )}
            <p className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">
              نص عادي فقط. لا تُستخدم وسوم HTML. عدد الأحرف:{" "}
              <span className="tabular-nums">{formatNumber(body.length)}</span>
            </p>
          </div>

          <VariablePalette
            variables={variables}
            error={variablesError}
            announcement={announcement}
            onInsert={insertVariable}
          />

          {error && (
            <p
              role="alert"
              className="rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] text-[var(--fd-red-text)]"
            >
              {error}
            </p>
          )}

          <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--fd-line)] pt-4">
            <Link href="/settings/templates" className="fd-btn fd-btn-secondary h-11">
              إلغاء
            </Link>
            <button type="submit" className="fd-btn fd-btn-primary h-11" disabled={saving}>
              <Save size={15} aria-hidden />
              {saving ? "جارٍ الحفظ…" : "حفظ كإصدار جديد"}
            </button>
          </div>
        </div>

        <aside className="space-y-4">
          <section className="fd-card fd-card-pad" aria-labelledby="template-checks">
            <h2 id="template-checks" className="text-sm font-semibold text-[var(--fd-ink)]">
              جاهزية القالب
            </h2>
            <ul className="mt-2 space-y-2 text-[12px]">
              <li className="flex items-center gap-2">
                {name.trim() ? (
                  <Check size={15} className="text-[var(--fd-green-text)]" aria-hidden />
                ) : (
                  <Minus size={15} className="text-[var(--fd-ink-subtle)]" aria-hidden />
                )}
                {name.trim() ? "الاسم جاهز" : "أدخل اسم القالب"}
              </li>
              <li className="flex items-center gap-2">
                {body.trim() ? (
                  <Check size={15} className="text-[var(--fd-green-text)]" aria-hidden />
                ) : (
                  <Minus size={15} className="text-[var(--fd-ink-subtle)]" aria-hidden />
                )}
                {body.trim() ? "النص جاهز" : "أدخل نص الرسالة"}
              </li>
              <li className="flex items-start gap-2">
                {unknownVariables.length === 0 ? (
                  <Check
                    size={15}
                    className="mt-0.5 text-[var(--fd-green-text)]"
                    aria-hidden
                  />
                ) : (
                  <TriangleAlert
                    size={15}
                    className="mt-0.5 text-[var(--fd-amber-text)]"
                    aria-hidden
                  />
                )}
                <span>
                  {unknownVariables.length === 0
                    ? "كل المتغيرات معروفة"
                    : "متغيرات غير معروفة: "}
                  {unknownVariables.map((variable, index) => (
                    <span key={variable}>
                      {index > 0 ? "، " : ""}
                      <bdi dir="ltr" lang="en">{`{{${variable}}}`}</bdi>
                    </span>
                  ))}
                </span>
              </li>
              {nextVersion != null && (
                <li className="text-[11px] text-[var(--fd-ink-muted)]">
                  سيُنشأ الإصدار {nextVersion} ويصبح النشط.
                </li>
              )}
            </ul>
            {unknownVariables.length > 0 && (
              <p className="mt-2 text-[11px] leading-5 text-[var(--fd-amber-text)]">
                يمكن الحفظ، لكن الحملات التي تستخدم هذا القالب لن تُعتمد.
              </p>
            )}
          </section>

          <section className="fd-card fd-card-pad" aria-labelledby="template-preview">
            <h2
              id="template-preview"
              className="text-sm font-semibold text-[var(--fd-ink)]"
            >
              معاينة النص
            </h2>
            <p className="mt-1 text-[11px] text-[var(--fd-ink-subtle)]">
              هكذا يظهر النص قبل استبدال المتغيرات.
            </p>
            <div className="mt-2">
              <TemplateBody body={body} ariaLabel="معاينة نص القالب" />
            </div>
          </section>
        </aside>
      </div>
    </form>
  );
}
