"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, LockKeyhole, UserRound } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { clearSession, primeSession } from "@/lib/session";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("reason") === "expired") {
      setError("انتهت الجلسة. يرجى تسجيل الدخول مجددًا.");
    }
  }, []);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const me = await api.login(username.trim(), password);
      clearSession();
      primeSession(me);
      router.replace(me.user.must_change_password ? "/change-password" : "/");
    } catch (err) {
      setError(err instanceof ApiError ? err.messageAr : "تعذر تسجيل الدخول. حاول مرة أخرى.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[var(--fd-bg)] p-4 md:p-8">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-6xl overflow-hidden rounded-[22px] border border-[var(--fd-line)] bg-[var(--fd-surface)] shadow-[var(--fd-shadow-pop)] lg:grid-cols-[0.95fr_1.05fr]">
        {/* The form comes first so it sits at the RTL reading start. */}
        <section className="flex items-center justify-center p-6 md:p-12">
          <div className="w-full max-w-sm">
            <div className="mb-6 flex items-center gap-2.5 lg:hidden">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--fd-brand-soft)] text-[var(--fd-brand)]">
                <BookOpen size={22} strokeWidth={1.8} aria-hidden />
              </span>
              <span className="font-serif text-lg font-bold tracking-tight text-[var(--fd-brand)]">
                FeeDesk
              </span>
            </div>

            <p className="text-xs font-medium text-[var(--fd-ink-subtle)]">مرحبًا بعودتك</p>
            <h1 className="mt-1 text-2xl font-bold text-[var(--fd-ink)]">تسجيل الدخول</h1>
            <p className="mt-2 text-[13px] leading-6 text-[var(--fd-ink-muted)]">
              استخدم الحساب الذي وفره مدير النظام.
            </p>

            <form onSubmit={onSubmit} className="mt-8 space-y-4">
              <div>
                <label htmlFor="username" className="fd-label">
                  اسم المستخدم
                </label>
                <div className="relative">
                  <UserRound
                    size={16}
                    className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[var(--fd-ink-subtle)]"
                    aria-hidden
                  />
                  <input
                    id="username"
                    name="username"
                    className="fd-input pr-9 text-left"
                    dir="ltr"
                    autoComplete="username"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="fd-label">
                  كلمة المرور
                </label>
                <div className="relative">
                  <LockKeyhole
                    size={16}
                    className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[var(--fd-ink-subtle)]"
                    aria-hidden
                  />
                  <input
                    id="password"
                    name="password"
                    type="password"
                    className="fd-input pr-9 text-left"
                    dir="ltr"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
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
                {loading ? "جارٍ تسجيل الدخول..." : "تسجيل الدخول"}
              </button>
            </form>

            <p className="mt-6 rounded-[var(--fd-radius-control)] bg-[var(--fd-surface-alt)] px-3 py-2 text-[11px] leading-5 text-[var(--fd-ink-muted)]">
              سيُطلب منك تغيير كلمة المرور المؤقتة عند أول دخول. لا تشارك بيانات الدخول مع أي شخص.
            </p>
          </div>
        </section>

        {/* Brand panel is desktop-only; phones get the compact logo above the form. */}
        <section className="relative hidden flex-col justify-between overflow-hidden bg-[var(--fd-brand)] p-8 text-white lg:flex lg:p-12">
          <div className="absolute -left-20 -top-24 h-64 w-64 rounded-full bg-white/5" aria-hidden />
          <div className="absolute -bottom-28 -right-16 h-72 w-72 rounded-full bg-white/5" aria-hidden />

          <div className="relative">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/10">
                <BookOpen size={24} strokeWidth={1.7} aria-hidden />
              </span>
              <div>
                <p className="font-serif text-2xl font-bold tracking-tight">FeeDesk</p>
                <p className="text-[11px] text-white/65">إدارة الأقساط</p>
              </div>
            </div>

            <p className="mt-14 max-w-md text-[32px] font-bold leading-[1.35]">
              أقساط واضحة،
              <br />
              وتذكيرات منظمة.
            </p>
            <p className="mt-4 max-w-sm text-sm leading-7 text-white/75">
              مساحة عمل هادئة لإدارة كشوف الأقساط، مراجعة المستحقات، واعتماد تذكيرات الدفع قبل إرسالها.
            </p>
          </div>

          <p className="relative text-[11px] text-white/70">دخول آمن للموظفين المعتمدين فقط.</p>
        </section>
      </div>
    </main>
  );
}
