"use client";

import { useEffect, useRef, useState } from "react";
import { KeyRound, Pencil, Power, UserPlus, X } from "lucide-react";
import { ApiError, api, roleLabel, type User } from "@/lib/api";
import { ensureMe } from "@/lib/session";
import { Protected } from "@/components/Protected";
import { PageHeader } from "@/components/PageHeader";
import { StatusPill } from "@/components/StatusPill";
import { CampaignApprovalField } from "@/components/CampaignApprovalField";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { UserEditDialog } from "@/components/UserEditDialog";

type Notice = { id: number; kind: "success" | "error"; text: string };
type PendingAction = { user: User; action: "deactivate" | "reset" };

function apiMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.messageAr : fallback;
}

export default function UsersSettingsPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    username: "",
    password: "",
    role: "staff",
    job_title: "",
    can_approve_campaigns: false,
  });
  const [notice, setNotice] = useState<Notice | null>(null);
  const noticeId = useRef(0);
  const [tempPassword, setTempPassword] = useState<{ username: string; password: string } | null>(
    null,
  );
  const [saving, setSaving] = useState(false);
  const [editTarget, setEditTarget] = useState<User | null>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [pendingBusy, setPendingBusy] = useState(false);
  const [pendingError, setPendingError] = useState<string | null>(null);

  function notify(kind: Notice["kind"], text: string) {
    noticeId.current += 1;
    setNotice({ id: noticeId.current, kind, text });
  }

  async function loadUsers() {
    try {
      setUsers(await api.listUsers());
    } catch (err) {
      notify("error", apiMessage(err, "تعذر تحميل المستخدمين."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
    let mounted = true;
    ensureMe()
      .then((me) => {
        if (mounted) setCurrentUserId(me.user.id);
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, []);

  async function onCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    try {
      await api.createUser({
        username: form.username.trim(),
        password: form.password,
        role: form.role,
        job_title: form.job_title || undefined,
        can_approve_campaigns:
          form.role === "staff" ? form.can_approve_campaigns : false,
      });
      setForm({
        username: "",
        password: "",
        role: "staff",
        job_title: "",
        can_approve_campaigns: false,
      });
      notify("success", "تم إنشاء المستخدم. سيُطلب منه تغيير كلمة المرور عند أول دخول.");
      await loadUsers();
    } catch (err) {
      notify("error", apiMessage(err, "تعذر إنشاء المستخدم."));
    } finally {
      setSaving(false);
    }
  }

  function openConfirm(user: User, action: PendingAction["action"]) {
    setTempPassword(null);
    setPendingError(null);
    setPendingBusy(false);
    setPending({ user, action });
  }

  async function changeActive(user: User, nextActive: boolean): Promise<boolean> {
    try {
      const updated = await api.updateUser(user.id, { is_active: nextActive });
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      notify(
        "success",
        nextActive ? `تم تفعيل حساب ${user.username}.` : `تم تعطيل حساب ${user.username}.`,
      );
      return true;
    } catch (err) {
      const text = apiMessage(err, nextActive ? "تعذر تفعيل الحساب." : "تعذر تعطيل الحساب.");
      if (nextActive) {
        notify("error", text);
      } else {
        setPendingError(text);
      }
      return false;
    }
  }

  async function runPendingAction() {
    if (!pending) return;
    setPendingBusy(true);
    setPendingError(null);

    if (pending.action === "reset") {
      try {
        const result = await api.resetUserPassword(pending.user.id);
        setTempPassword({ username: pending.user.username, password: result.temporary_password });
        notify("success", `تم إنشاء كلمة مرور مؤقتة لـ ${pending.user.username}.`);
        setPending(null);
      } catch (err) {
        setPendingError(apiMessage(err, "تعذر إعادة تعيين كلمة المرور."));
      } finally {
        setPendingBusy(false);
      }
      return;
    }

    const ok = await changeActive(pending.user, false);
    setPendingBusy(false);
    if (ok) setPending(null);
  }

  function onToggle(user: User) {
    if (user.is_active) {
      openConfirm(user, "deactivate");
    } else {
      void changeActive(user, true);
    }
  }

  function onUserSaved(updated: User) {
    setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    setEditTarget(null);
    notify("success", `تم تحديث بيانات ${updated.username}.`);
  }

  const pendingIsSelf = pending !== null && pending.user.id === currentUserId;

  return (
    <Protected active="/settings" requireAdmin>
      <PageHeader
        title="إدارة المستخدمين"
        subtitle="حسابات الموظفين وصلاحياتهم. تغيير الدور أو التعطيل يُسجَّل في سجل العمليات."
      />

      {notice && (
        <p
          key={notice.id}
          role={notice.kind === "error" ? "alert" : "status"}
          aria-atomic="true"
          className={`mb-4 rounded-[var(--fd-radius-control)] px-3 py-2 text-[12px] ${
            notice.kind === "success"
              ? "bg-[var(--fd-green-soft)] text-[var(--fd-green-text)]"
              : "bg-[var(--fd-red-soft)] text-[var(--fd-red-text)]"
          }`}
        >
          {notice.text}
        </p>
      )}

      {tempPassword && (
        <div
          role="status"
          aria-live="polite"
          className="mb-4 rounded-[var(--fd-radius-control)] border border-[var(--fd-line-strong)] bg-[var(--fd-amber-soft)] px-3 py-2 text-[12px] text-[var(--fd-amber-text)]"
        >
          <div className="flex items-start justify-between gap-3">
            <p>
              كلمة المرور المؤقتة لـ <span className="font-semibold">{tempPassword.username}</span>:{" "}
              <span className="font-mono font-semibold" dir="ltr">
                {tempPassword.password}
              </span>
              <span className="ms-2">— اعرضها للمستخدم مرة واحدة ثم أغلق الصفحة.</span>
            </p>
            <button
              type="button"
              onClick={() => setTempPassword(null)}
              className="fd-btn fd-btn-ghost h-11 w-11 shrink-0 px-0 text-[var(--fd-amber-text)]"
              aria-label="إخفاء كلمة المرور المؤقتة"
            >
              <X size={14} aria-hidden />
            </button>
          </div>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
        <form onSubmit={onCreate} className="fd-card fd-card-pad">
          <div className="mb-4 flex items-center gap-2">
            <UserPlus size={17} className="text-[var(--fd-brand)]" aria-hidden />
            <h2 className="text-sm font-semibold text-[var(--fd-ink)]">إضافة مستخدم</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label htmlFor="new_username" className="fd-label">اسم المستخدم</label>
              <input
                id="new_username"
                className="fd-input h-11 text-left"
                dir="ltr"
                value={form.username}
                onChange={(event) => setForm({ ...form, username: event.target.value })}
                minLength={3}
                maxLength={80}
                required
                disabled={saving}
                autoComplete="off"
              />
            </div>
            <div>
              <label htmlFor="new_password" className="fd-label">كلمة مرور مؤقتة</label>
              <input
                id="new_password"
                type="password"
                className="fd-input h-11 text-left"
                dir="ltr"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                minLength={12}
                maxLength={200}
                required
                disabled={saving}
                autoComplete="new-password"
              />
            </div>
            <div>
              <label htmlFor="new_role" className="fd-label">الدور</label>
              <select
                id="new_role"
                className="fd-input h-11"
                value={form.role}
                onChange={(event) => {
                  const role = event.target.value;
                  setForm((current) => ({
                    ...current,
                    role,
                    can_approve_campaigns:
                      role === "staff" ? current.can_approve_campaigns : false,
                  }));
                }}
                disabled={saving}
              >
                <option value="staff">موظف إداري</option>
                <option value="admin">مدير النظام</option>
              </select>
            </div>
            <CampaignApprovalField
              id="new_can_approve_campaigns"
              role={form.role}
              checked={form.can_approve_campaigns}
              disabled={saving}
              onChange={(checked) =>
                setForm((current) => ({ ...current, can_approve_campaigns: checked }))
              }
            />
            <div>
              <label htmlFor="new_job_title" className="fd-label">المسمى الوظيفي</label>
              <input
                id="new_job_title"
                className="fd-input h-11"
                value={form.job_title}
                onChange={(event) => setForm({ ...form, job_title: event.target.value })}
                maxLength={120}
                placeholder="مثال: موظف إداري"
                disabled={saving}
              />
            </div>
          </div>

          <button type="submit" className="fd-btn fd-btn-primary mt-5 h-11 w-full" disabled={saving}>
            {saving ? "جارٍ الإنشاء..." : "إنشاء المستخدم"}
          </button>
        </form>

        <section className="fd-card overflow-hidden" aria-labelledby="users-table-title">
          <div className="border-b border-[var(--fd-line)] px-5 py-4">
            <h2 id="users-table-title" className="text-sm font-semibold text-[var(--fd-ink)]">
              المستخدمون
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="fd-table min-w-0 lg:min-w-[680px]">
              <caption className="sr-only">قائمة المستخدمين وإجراءات إدارتها</caption>
              <thead>
                <tr>
                  <th scope="col">المستخدم</th>
                  <th scope="col">الدور</th>
                  <th scope="col">الحالة</th>
                  <th scope="col" className="w-[1%] whitespace-nowrap">
                    <span className="sr-only">إجراءات</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => {
                  const isSelf = user.id === currentUserId;
                  return (
                    <tr key={user.id}>
                      <td>
                        <p className="flex flex-wrap items-center gap-1.5 font-medium text-[var(--fd-ink)]">
                          <span dir="ltr">{user.username}</span>
                          {isSelf && <StatusPill tone="neutral">أنت</StatusPill>}
                          {user.role === "staff" && user.can_approve_campaigns && (
                            <StatusPill tone="green">يعتمد الحملات</StatusPill>
                          )}
                        </p>
                        <p className="break-words text-[11px] text-[var(--fd-ink-subtle)]">
                          {user.job_title || roleLabel(user.role)}
                          {user.email && (
                            <>
                              {" · "}
                              <span dir="ltr" className="break-all">{user.email}</span>
                            </>
                          )}
                        </p>
                      </td>
                      <td>{roleLabel(user.role)}</td>
                      <td>
                        {user.is_active ? (
                          <StatusPill tone="green">نشط</StatusPill>
                        ) : (
                          <StatusPill tone="neutral">معطّل</StatusPill>
                        )}
                      </td>
                      <td>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => setEditTarget(user)}
                            className="fd-btn fd-btn-ghost h-11 w-11 shrink-0 px-0"
                            aria-label={`تعديل بيانات ${user.username}`}
                            title="تعديل البيانات"
                          >
                            <Pencil size={16} aria-hidden />
                          </button>
                          <button
                            type="button"
                            onClick={() => openConfirm(user, "reset")}
                            className="fd-btn fd-btn-ghost h-11 w-11 shrink-0 px-0"
                            aria-label={`إعادة تعيين كلمة مرور ${user.username}`}
                            title="إعادة تعيين كلمة المرور"
                          >
                            <KeyRound size={16} aria-hidden />
                          </button>
                          <button
                            type="button"
                            onClick={() => onToggle(user)}
                            className="fd-btn fd-btn-ghost h-11 w-11 shrink-0 px-0"
                            aria-label={
                              isSelf
                                ? "لا يمكنك تعطيل حسابك الحالي"
                                : user.is_active
                                  ? `تعطيل حساب ${user.username}`
                                  : `تفعيل حساب ${user.username}`
                            }
                            title={
                              isSelf && user.is_active
                                ? "لا يمكنك تعطيل حسابك الحالي"
                                : user.is_active
                                  ? "تعطيل الحساب"
                                  : "تفعيل الحساب"
                            }
                            disabled={isSelf && user.is_active}
                          >
                            <Power size={16} aria-hidden />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {!loading && users.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-10 text-center text-[13px] text-[var(--fd-ink-muted)]">
                      لا يوجد مستخدمون بعد.
                    </td>
                  </tr>
                )}
                {loading && (
                  <tr>
                    <td colSpan={4} className="py-10 text-center text-[13px] text-[var(--fd-ink-muted)]">
                      جارٍ تحميل المستخدمين...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {editTarget && (
        <UserEditDialog
          key={editTarget.id}
          user={editTarget}
          isSelf={editTarget.id === currentUserId}
          onClose={() => setEditTarget(null)}
          onSaved={onUserSaved}
        />
      )}

      <ConfirmDialog
        open={pending !== null}
        title={pending?.action === "reset" ? "إعادة تعيين كلمة المرور؟" : "تعطيل الحساب؟"}
        description={
          pending?.action === "reset" ? (
            <>
              ستُنشأ كلمة مرور مؤقتة جديدة لـ{" "}
              <span className="font-semibold text-[var(--fd-ink)]">{pending.user.username}</span>{" "}
              وتُلغى جميع جلساته الحالية.
              {pendingIsSelf && " سيتم إنهاء جلستك الحالية أيضًا."}
            </>
          ) : pending ? (
            <>
              سيتوقف{" "}
              <span className="font-semibold text-[var(--fd-ink)]">{pending.user.username}</span>{" "}
              عن تسجيل الدخول فورًا. يمكنك إعادة تفعيل الحساب لاحقًا.
            </>
          ) : null
        }
        confirmLabel={
          pending?.action === "reset" ? "إعادة تعيين كلمة المرور" : "تعطيل الحساب"
        }
        busyLabel={pending?.action === "reset" ? "جارٍ إعادة التعيين..." : "جارٍ التعطيل..."}
        busy={pendingBusy}
        error={pendingError}
        onConfirm={() => void runPendingAction()}
        onClose={() => {
          if (pendingBusy) return;
          setPending(null);
          setPendingError(null);
        }}
      />
    </Protected>
  );
}
