import { BookOpen } from "lucide-react";

export function Logo({ compact = false, tagline = "إدارة الأقساط" }: { compact?: boolean; tagline?: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--fd-brand-soft)] text-[var(--fd-brand)]">
        <BookOpen size={22} strokeWidth={1.8} aria-hidden />
      </span>
      {!compact && (
        <span className="fd-logo-text leading-tight">
          <span className="block font-serif text-xl font-bold tracking-tight text-[var(--fd-brand)]">
            FeeDesk
          </span>
          <span className="block max-w-[150px] truncate text-[10px] text-[var(--fd-ink-muted)]" title={tagline}>
            {tagline}
          </span>
        </span>
      )}
    </div>
  );
}
