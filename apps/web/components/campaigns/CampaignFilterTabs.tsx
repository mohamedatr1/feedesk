"use client";

import Link from "next/link";
import { ChevronLeft } from "lucide-react";

export function CampaignFilterTabs({
  current,
  counts,
}: {
  current: string;
  counts: Record<string, number | null>;
}) {
  const tabs: Array<{ value: string; label: string; href: string }> = [
    { value: "", label: "الكل", href: "/campaigns" },
    { value: "draft", label: "مسودة", href: "/campaigns?status=draft" },
    {
      value: "awaiting_approval",
      label: "بانتظار الاعتماد",
      href: "/campaigns?status=awaiting_approval",
    },
    { value: "approved", label: "معتمدة", href: "/campaigns?status=approved" },
    { value: "cancelled", label: "ملغاة", href: "/campaigns?status=cancelled" },
  ];

  return (
    <nav
      aria-label="تصفية الحملات حسب الحالة"
      className="flex flex-wrap items-center gap-1 rounded-[var(--fd-radius-control)] border border-[var(--fd-line)] bg-[var(--fd-surface)] p-1"
    >
      {tabs.map((tab) => {
        const active = current === tab.value;
        const count = counts[tab.value];
        return (
          <Link
            key={tab.value || "all"}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={`inline-flex min-h-11 items-center gap-1.5 rounded-[var(--fd-radius-control)] px-3 py-2 text-[13px] font-medium transition ${
              active
                ? "bg-[var(--fd-brand)] text-white"
                : "text-[var(--fd-ink-muted)] hover:bg-[var(--fd-surface-alt)]"
            }`}
          >
            {tab.label}
            {count != null && (
              <span
                className={`tabular-nums text-[11px] ${
                  active ? "text-white/80" : "text-[var(--fd-ink-subtle)]"
                }`}
              >
                {count.toLocaleString("en-US")}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}

export function CampaignBreadcrumb({ label }: { label?: string }) {
  return (
    <nav aria-label="مسار التصفح" className="mb-3">
      <ol className="flex flex-wrap items-center gap-1 text-[12px] text-[var(--fd-ink-muted)]">
        <li>
          <Link href="/campaigns" className="hover:text-[var(--fd-ink)] hover:underline">
            الحملات
          </Link>
        </li>
        {label && (
          <>
            <li aria-hidden>
              <ChevronLeft size={14} className="rtl:rotate-180" />
            </li>
            <li aria-current="page" className="min-w-0 text-[var(--fd-ink)]">
              <bdi dir="auto" className="truncate">
                {label}
              </bdi>
            </li>
          </>
        )}
      </ol>
    </nav>
  );
}
