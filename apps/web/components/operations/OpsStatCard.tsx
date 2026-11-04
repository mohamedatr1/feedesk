import Link from "next/link";
import { ArrowUpLeft } from "lucide-react";
import type { LucideIcon } from "lucide-react";

type Tone = "neutral" | "amber" | "green" | "red";

/** Static maps only: Tailwind cannot see a class built from a variable. */
const DOT: Record<Tone, string> = {
  neutral: "bg-[var(--fd-line-strong)]",
  amber: "bg-[var(--fd-amber)]",
  green: "bg-[var(--fd-green)]",
  red: "bg-[var(--fd-red)]",
};

/**
 * A counting card in the product's StatCard language, extended with a tone
 * marker and an optional list link. Tone is only a supporting cue: the number,
 * label and hint always carry the meaning.
 */
export function OpsStatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "neutral",
  href,
  linkLabel,
}: {
  label: string;
  value: string;
  hint: string;
  icon: LucideIcon;
  tone?: Tone;
  href?: string;
  linkLabel?: string;
}) {
  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <p className="flex min-w-0 items-baseline gap-2 text-[13px] font-medium text-[var(--fd-ink-muted)]">
          <span aria-hidden className={`h-2 w-2 shrink-0 rounded-full ${DOT[tone]}`} />
          <span>{label}</span>
        </p>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--fd-surface-alt)] text-[var(--fd-ink-muted)]">
          <Icon size={18} strokeWidth={1.8} aria-hidden />
        </span>
      </div>

      <p className="fd-stat-value mt-3">{value}</p>

      <p className="mt-2 flex-1 text-[11px] leading-5 text-[var(--fd-ink-subtle)]">{hint}</p>

      {href && linkLabel && (
        <span className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-[var(--fd-brand)]">
          {linkLabel}
          <ArrowUpLeft size={12} aria-hidden />
        </span>
      )}
    </>
  );

  if (!href) {
    return <div className="fd-card fd-card-pad flex flex-col">{body}</div>;
  }

  return (
    <Link
      href={href}
      className="fd-card fd-card-pad flex flex-col transition hover:border-[var(--fd-line-strong)]"
    >
      {body}
    </Link>
  );
}
