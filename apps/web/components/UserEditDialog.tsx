"use client";

import { useState } from "react";
import { Save } from "lucide-react";
import { ApiError, api, roleLabel, type User } from "@/lib/api";
import { CampaignApprovalField } from "@/components/CampaignApprovalField";
import { Dialog } from "@/components/Dialog";

export function UserEditDialog({
  user,
  isSelf,
  onClose,
  onSaved,
}: {
  user: User;
  isSelf: boolean;
  onClose: () => void;
  onSaved: (updated: User) => void;
}) {
  const initialRole = user.role === "admin" ? "admin" : "staff";
  const [form, setForm] = useState({
    email: user.email ?? "",
    role: initialRole,
    job_title: user.job_title ?? "",
    // Admin approval is implicit, so the flag only ever applies to staff.
    can_approve_campaigns:
      initialRole === "staff" ? Boolean(user.can_approve_campaigns) : false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const emailId = `edit_user_email_${user.id}`;
  const roleId = `edit_user_role_${user.id}`;
  const jobTitleId = `edit_user_job_title_${user.id}`;
  const approvalId = `edit_user_approval_${user.id}`;

  function onRoleChange(role: string) {
    setForm((current) => ({
      ...current,
      role,
      can_approve_campaigns:
        role === "staff" ? current.can_approve_campaigns : false,
    }));
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateUser(user.id, {
        email: form.email.trim() || null,
        role: form.role,
        job_title: form.job_title.trim() || null,
        can_approve_campaigns:
          form.role === "staff" ? form.can_approve_campaigns : false,
      });
      onSaved(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.messageAr : "تعذر تحديث بيانات المستخدم.");
      setSaving(false);
    }
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title="تعديل بيانات المستخدم"
      description="يمكن تعديل الدور والبريد الإلكتروني والمسمى الوظيفي وصلاحية اعتماد الحملات. اسم المستخدم غير قابل للتغيير."
      busy={saving}
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] bg-[var(--fd-surface-alt)] px-3 py-2">
          <p className="fd-label mb-1">اسم المستخدم</p>
          <p className="font-mono text-[13px] font-medium text-[var(--fd-ink)]" dir="ltr">
            {user.username}
          </p>
        </div>

        <div>
          <label htmlFor={emailId} className="fd-label">
            البريد الإلكتروني
          </label>
          <input
            id={emailId}
            type="email"
            className="fd-input h-11 text-left"
            dir="ltr"
            maxLength={255}
            autoComplete="off"
            placeholder="اختياري"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            disabled={saving}
            data-autofocus
          />
        </div>

        <div>
          <label htmlFor={roleId} className="fd-label">
            الدور
          </label>
          <select
            id={roleId}
            className="fd-input h-11"
            value={form.role}
            onChange={(event) => onRoleChange(event.target.value)}
            disabled={saving}
          >
            <option value="staff">{roleLabel("staff")}</option>
            <option value="admin">{roleLabel("admin")}</option>
          </select>
          {isSelf && user.role === "admin" && form.role !== "admin" && (
            <p className="mt-1.5 text-[11px] leading-5 text-[var(--fd-amber-text)]">
              تنبيه: خفض دورك الحالي سيمنعك من إدارة المستخدمين بمجرد حفظ التغيير.
            </p>
          )}
        </div>

        <CampaignApprovalField
          id={approvalId}
          role={form.role}
          checked={form.can_approve_campaigns}
          disabled={saving}
          onChange={(checked) =>
            setForm((current) => ({ ...current, can_approve_campaigns: checked }))
          }
        />

        <div>
          <label htmlFor={jobTitleId} className="fd-label">
            المسمى الوظيفي
          </label>
          <input
            id={jobTitleId}
            className="fd-input h-11"
            maxLength={120}
            placeholder="اختياري"
            value={form.job_title}
            onChange={(event) => setForm({ ...form, job_title: event.target.value })}
            disabled={saving}
          />
        </div>

        {error && (
          <p
            role="alert"
            className="rounded-[var(--fd-radius-control)] bg-[var(--fd-red-soft)] px-3 py-2 text-[12px] text-[var(--fd-red-text)]"
          >
            {error}
          </p>
        )}

        <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--fd-line)] pt-4">
          <button
            type="button"
            className="fd-btn fd-btn-secondary h-11"
            onClick={onClose}
            disabled={saving}
          >
            إلغاء
          </button>
          <button type="submit" className="fd-btn fd-btn-primary h-11" disabled={saving}>
            <Save size={15} aria-hidden />
            {saving ? "جارٍ الحفظ..." : "حفظ التعديلات"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
