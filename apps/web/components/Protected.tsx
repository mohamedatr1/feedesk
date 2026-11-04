"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldAlert } from "lucide-react";
import { ApiError, type Me, type SchoolSettings } from "@/lib/api";
import { AppShell } from "@/components/AppShell";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import {
  SessionProvider,
  clearSession,
  ensureMe,
  ensureSettings,
  getCachedMe,
  getCachedSettings,
} from "@/lib/session";

export function Protected({
  children,
  active,
  requireAdmin = false,
}: {
  children: React.ReactNode;
  active?: string;
  requireAdmin?: boolean;
}) {
  const router = useRouter();
  // Seed from the session cache so client-side navigation renders the shell
  // immediately instead of flashing a full-screen skeleton.
  const [me, setMe] = useState<Me | null>(() => getCachedMe());
  const [settings, setSettings] = useState<SchoolSettings | null>(() => getCachedSettings());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadMe(attempt = 1): Promise<Me> {
      try {
        return await ensureMe();
      } catch (err) {
        // A Vercel cold start can surface as a one-off 5xx/network failure.
        // Retry once before showing the full-page error.
        if (
          attempt < 2 &&
          !(err instanceof ApiError && err.status >= 400 && err.status < 500)
        ) {
          await new Promise((resolve) => setTimeout(resolve, 500));
          return loadMe(attempt + 1);
        }
        throw err;
      }
    }

    loadMe()
      .then((data) => {
        if (!mounted) return;
        if (data.user.must_change_password) {
          router.replace("/change-password");
          return;
        }
        setMe(data);
        // Cached settings resolve without another network round-trip.
        return ensureSettings()
          .then((value) => {
            if (mounted) setSettings(value);
          })
          .catch(() => undefined);
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 401) {
          clearSession();
          router.replace("/login?reason=expired");
          return;
        }
        setError(
          err instanceof ApiError
            ? err.messageAr
            : err instanceof Error
              ? err.message
              : "تعذر تحميل بيانات الجلسة.",
        );
      });

    return () => {
      mounted = false;
    };
  }, [router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <div className="fd-card fd-card-pad max-w-md text-center">
          <p className="text-sm font-semibold text-[var(--fd-red-text)]">تعذر تحميل الصفحة</p>
          <p className="mt-2 text-[13px] text-[var(--fd-ink-muted)]">{error}</p>
          <button className="fd-btn fd-btn-primary mt-4" onClick={() => window.location.reload()}>
            إعادة المحاولة
          </button>
        </div>
      </div>
    );
  }

  if (!me || me.user.must_change_password) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="w-full max-w-sm space-y-3 px-6">
          <div className="fd-skeleton h-10 w-40" />
          <div className="fd-skeleton h-24 w-full" />
          <div className="fd-skeleton h-24 w-full" />
        </div>
      </div>
    );
  }

  if (requireAdmin && me.user.role !== "admin") {
    return (
      <SessionProvider user={me.user} settings={settings}>
        <AppShell user={me.user} active={active} settings={settings}>
          <PageHeader title="غير مصرح" subtitle="هذه الصفحة مخصصة لمدير النظام." />
          <div className="fd-card">
            <EmptyState
              icon={ShieldAlert}
              title="لا تملك صلاحية الوصول"
              description="يمكنك العودة إلى الرئيسية أو التواصل مع مدير النظام إذا كنت تعتقد أن هذا خطأ."
              action={
                <a className="fd-btn fd-btn-secondary" href="/">
                  العودة إلى الرئيسية
                </a>
              }
            />
          </div>
        </AppShell>
      </SessionProvider>
    );
  }

  return (
    <SessionProvider user={me.user} settings={settings}>
      <AppShell user={me.user} active={active} settings={settings}>
        {children}
      </AppShell>
    </SessionProvider>
  );
}
