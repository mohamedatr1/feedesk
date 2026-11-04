export function StatusPill({
  tone,
  children,
}: {
  tone: "neutral" | "amber" | "green" | "red";
  children: React.ReactNode;
}) {
  return (
    <span className={`fd-pill fd-pill-${tone}`}>
      <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}
