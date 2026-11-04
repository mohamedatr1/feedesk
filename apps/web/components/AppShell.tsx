"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Bell,
  CalendarDays,
  FileText,
  History,
  Home,
  LogOut,
  Megaphone,
  Menu,
  MessageSquare,
  Settings,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api, formatDate, roleLabel, type SchoolSettings, type User } from "@/lib/api";
import { clearSession } from "@/lib/session";
import { Logo } from "@/components/Logo";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  adminOnly?: boolean;
};

const NAV: NavItem[] = [
  { href: "/", label: "الرئيسية", icon: Home },
  { href: "/statements", label: "كشوف الأقساط", icon: FileText },
  { href: "/campaigns", label: "الحملات", icon: Megaphone },
  { href: "/messages", label: "سجل الرسائل", icon: MessageSquare },
  { href: "/operations", label: "عمليات الرسائل", icon: Activity, adminOnly: true },
  { href: "/audit", label: "سجل العمليات", icon: History, adminOnly: true },
  // Settings is read-only for staff, so it must stay visible for both roles.
  { href: "/settings", label: "الإعدادات", icon: Settings },
];

export function AppShell({
  user,
  active,
  settings,
  children,
}: {
  user: User;
  active?: string;
  settings?: SchoolSettings | null;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [navOpen, setNavOpen] = useState(false);
  const current = active ?? pathname;
  const schoolName = settings?.school_name || "إدارة الأقساط";

  useEffect(() => {
    setNavOpen(false);
  }, [pathname]);

  const toggleNav = useCallback(() => setNavOpen((open) => !open), []);
  const closeNav = useCallback(() => setNavOpen(false), []);

  async function handleLogout() {
    try {
      await api.logout();
    } finally {
      clearSession();
      window.location.href = "/login";
    }
  }

  return (
    <div className={`fd-shell ${navOpen ? "fd-nav-open" : ""}`}>
      <a href="#main" className="fd-skip-link">
        تخطَّ إلى المحتوى
      </a>

      <button
        type="button"
        className="fd-nav-backdrop"
        onClick={closeNav}
        aria-label="إغلاق القائمة"
        tabIndex={navOpen ? 0 : -1}
      />
      <aside className="fd-sidebar" aria-hidden={false}>
        <div className="mb-8 flex items-center justify-between gap-3 lg:justify-start">
          <Logo tagline={schoolName} />
          <button
            type="button"
            onClick={closeNav}
            className="fd-menu-button flex h-11 w-11 items-center justify-center rounded-[var(--fd-radius-control)] text-[var(--fd-ink-muted)] hover:bg-[var(--fd-surface-alt)] lg:hidden"
            aria-label="إغلاق القائمة"
          >
            <X size={20} aria-hidden />
          </button>
        </div>

        <nav id="primary-nav" aria-label="التنقل الرئيسي" className="space-y-1">
          {NAV.filter((item) => !item.adminOnly || user.role === "admin").map((item) => {
            const Icon = item.icon;
            const isActive = current === item.href || (item.href !== "/" && current.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`fd-nav-item ${isActive ? "fd-nav-item-active" : ""}`}
                aria-current={isActive ? "page" : undefined}
                aria-label={item.label}
                title={item.label}
              >
                <Icon size={18} strokeWidth={1.8} aria-hidden />
                <span className="fd-nav-label">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto pt-6 text-center">
          <p className="fd-sidebar-footer-text text-[11px] text-[var(--fd-ink-muted)]">v0.1.0</p>
        </div>
      </aside>

      <div className="fd-main">
        <header className="fd-topbar">
          <div className="flex items-center gap-2 sm:gap-4">
            <button
              type="button"
              onClick={toggleNav}
              className="fd-menu-button flex h-11 w-11 items-center justify-center rounded-[var(--fd-radius-control)] text-[var(--fd-ink-muted)] hover:bg-[var(--fd-surface-alt)]"
              aria-label="فتح القائمة"
              aria-expanded={navOpen}
              aria-controls="primary-nav"
            >
              <Menu size={20} aria-hidden />
            </button>
            <div className="flex items-center gap-2 text-[12px] text-[var(--fd-ink-muted)]">
              <CalendarDays size={16} aria-hidden className="shrink-0" />
              <span className="max-w-[42vw] truncate sm:max-w-none">
                {formatDate(new Date(), {
                  locale: settings?.locale,
                  timeZone: settings?.timezone,
                })}
              </span>
            </div>
            <button
              type="button"
              className="relative flex h-9 w-9 items-center justify-center rounded-full text-[var(--fd-ink-muted)] hover:bg-[var(--fd-surface-alt)]"
              aria-label="التنبيهات"
              title="التنبيهات"
            >
              <Bell size={18} aria-hidden />
            </button>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-left">
              <p className="text-sm font-semibold text-[var(--fd-ink)]">
                <bdi>{user.username}</bdi>
              </p>
              <p className="text-[11px] text-[var(--fd-ink-subtle)]">
                {user.job_title || roleLabel(user.role)}
              </p>
            </div>
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--fd-surface-alt)] text-sm font-semibold text-[var(--fd-ink-muted)]">
              {user.username.slice(0, 1).toUpperCase()}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="flex h-9 w-9 items-center justify-center rounded-full text-[var(--fd-ink-muted)] hover:bg-[var(--fd-red-soft)] hover:text-[var(--fd-red-text)]"
              aria-label="تسجيل الخروج"
              title="تسجيل الخروج"
            >
              <LogOut size={18} aria-hidden />
            </button>
          </div>
        </header>

        <main id="main" tabIndex={-1} className="fd-content pt-7 focus:outline-none">
          {children}
        </main>
      </div>
    </div>
  );
}
