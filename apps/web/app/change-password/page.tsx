"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, Eye, EyeOff, KeyRound, LogOut } from "lucide-react";
import { ApiError, api, type Me } from "@/lib/api";
import { clearSession, ensureMe } from "@/lib/session";

export default function ChangePasswordPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    ensureMe()
      .then(setMe)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) {
          clearSession();
          router.replace("/login?reason=expired");
        }
      });
  }, [router]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (newPassword.length < 12) {
      setError("كلمة المرور الجديدة يجب أن تكون 12 حرفًا على الأقل.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("كلمتا المرور غير متطابقتين.");
      return;
    }
    setLoading(true);
    try {
      await api.changePassword(currentPassword, newPassword);
      // The session's must_change_password flag changed server-side.
      clearSession();
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.messageAr : "تعذر تغيير كلمة المرور.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSignOut() {
    try {
      await api.logout();
    } finally {
      clearSession();
      window.location.href = "/login";
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--fd-bg)] px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-center gap-2.5">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--fd-brand-soft)] text-[var(--fd-brand)]">
            <BookOpen size={22} strokeWidth={1.8} aria-hidden />
          </span>
          <span className="font-serif text-xl font-bold text-[var(--fd-brand)]">FeeDesk</span>
        </div>

        <div className="fd-card fd-card-pad">
          <div className="mb-5">
            <span className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-[var(--fd-brand-soft)] text-[var(--fd-brand)]">
              <KeyRound size={17} aria-hidden />
            </span>
            <h1 className="text-2xl font-bold text-[var(--fd-ink)]">تغيير كلمة المرور</h1>
            <p className="mt-1 text-[12px] leading-5 text-[var(--fd-ink-muted)]">
              {me?.user.must_change_password
                ? "يجب تغيير كلمة المرور المؤقتة قبل استخدام النظام."
                : "يمكنك تحديث كلمة المرور من هنا."}
            </p>
            {me && (
              <p className="mt-2 text-[12px] text-[var(--fd-ink-muted)]">
                الحساب:{" "}
                <bdi className="font-medium text-[var(--fd-ink)]" dir="ltr">
                  {me.user.username}
                </bdi>
              </p>
            )}
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label htmlFor="current" className="fd-label">
                كلمة المرور الحالية
              </label>
              <input
                id="current"
                type="password"
                className="fd-input text-left"
                dir="ltr"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                required
                disabled={loading}
              />
            </div>
            <div>
              <label htmlFor="new" className="fd-label">
                كلمة المرور الجديدة
              </label>
              <div className="relative">
                <input
                  id="new"
                  type={showPassword ? "text" : "password"}
                  className="fd-input pr-11 text-left"
                  dir="ltr"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  aria-describedby="new-password-help"
                  required
                  minLength={12}
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}
                  aria-pressed={showPassword}
                  className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-[var(--fd-radius-control)] text-[var(--fd-ink-muted)] hover:text-[var(--fd-ink)]"
                >
                  {showPassword ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
                </button>
              </div>
              <p id="new-password-help" className="mt-1 text-[11px] text-[var(--fd-ink-muted)]">
                12 حرفًا على الأقل.
              </p>
            </div>
            <div>
              <label htmlFor="confirm" className="fd-label">
                تأكيد كلمة المرور
              </label>
              <input
                id="confirm"
                type={showPassword ? "text" : "password"}
                className="fd-input text-left"
                dir="ltr"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
                minLength={12}
                disabled={loading}
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

            <button type="submit" className="fd-btn fd-btn-primary w-full" disabled={loading}>
              {loading ? "جارٍ الحفظ..." : "حفظ كلمة المرور"}
            </button>
          </form>
        </div>

        <div className="mt-4 flex items-center justify-between gap-3 text-[12px] text-[var(--fd-ink-muted)]">
          <span>دخول آمن للموظفين المعتمدين فقط.</span>
          <button
            type="button"
            onClick={handleSignOut}
            className="inline-flex items-center gap-1.5 font-medium text-[var(--fd-brand)] hover:underline"
          >
            <LogOut size={14} aria-hidden />
            تسجيل الخروج
          </button>
        </div>
      </div>
    </main>
  );
}
