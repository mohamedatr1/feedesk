"use client";

import { ShieldCheck } from "lucide-react";

/**
 * Per-user campaign approval grant (FND-08). Admin approval is implicit, so the
 * checkbox is reserved for staff; switching the role to admin clears it.
 */
export function CampaignApprovalField({
  id,
  checked,
  role,
  disabled = false,
  onChange,
}: {
  id: string;
  checked: boolean;
  role: string;
  disabled?: boolean;
  onChange: (checked: boolean) => void;
}) {
  const isAdmin = role === "admin";
  const helpId = `${id}_help`;
  const adminNoteId = `${id}_admin_note`;

  return (
    <div className="rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] bg-[var(--fd-surface-alt)] p-3">
      <label
        htmlFor={id}
        className={`flex min-h-11 items-start gap-3 ${
          isAdmin ? "cursor-not-allowed" : "cursor-pointer"
        }`}
      >
        <input
          id={id}
          type="checkbox"
          className="mt-1 h-5 w-5 shrink-0 accent-[var(--fd-brand)]"
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
          disabled={disabled || isAdmin}
          aria-describedby={isAdmin ? `${helpId} ${adminNoteId}` : helpId}
        />
        <span className="flex items-center gap-1.5 text-[13px] font-medium text-[var(--fd-ink)]">
          <ShieldCheck
            size={15}
            className={isAdmin ? "text-[var(--fd-ink-subtle)]" : "text-[var(--fd-brand)]"}
            aria-hidden
          />
          يمكنه اعتماد الحملات
        </span>
      </label>
      <p
        id={helpId}
        className="mt-1 ps-8 text-[11px] leading-5 text-[var(--fd-ink-muted)]"
      >
        يمنح اعتماد الحملات فقط، ولا يمنح إدارة الإعدادات أو المستخدمين أو القوالب.
      </p>
      {isAdmin && (
        <p
          id={adminNoteId}
          className="mt-1 ps-8 text-[11px] leading-5 text-[var(--fd-ink-subtle)]"
        >
          مدير النظام يعتمد الحملات تلقائيًا، لذلك لا يلزم تفعيل هذا الخيار.
        </p>
      )}
    </div>
  );
}
