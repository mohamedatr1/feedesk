/**
 * A quiet decorative sparkline. The delta text beside/above it carries the
 * meaning, so the line is aria-hidden and disappears below two points.
 */
export function Sparkline({
  points,
  tone,
  compact = false,
}: {
  points: number[];
  tone: "green" | "red" | "neutral";
  /** A smaller line used when several currencies share one card. */
  compact?: boolean;
}) {
  if (points.length < 2) return null;

  const width = compact ? 56 : 96;
  const height = compact ? 20 : 28;
  const pad = compact ? 2 : 3;

  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min;
  const step = (width - pad * 2) / (points.length - 1);

  const coords = points.map((value, index) => {
    const ratio = span === 0 ? 0.5 : (value - min) / span;
    const x = pad + index * step;
    const y = height - pad - ratio * (height - pad * 2);
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });

  const stroke =
    tone === "green"
      ? "var(--fd-green)"
      : tone === "red"
        ? "var(--fd-red)"
        : "var(--fd-line-strong)";

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      aria-hidden="true"
      focusable="false"
      className={`shrink-0 ${compact ? "h-5 w-14" : "h-7 w-24"}`}
    >
      <polyline
        points={coords.join(" ")}
        fill="none"
        stroke={stroke}
        strokeWidth={1.6}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
