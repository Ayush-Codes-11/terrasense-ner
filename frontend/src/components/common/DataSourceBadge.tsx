// ============================================================
// DataSourceBadge — reusable "Sample" / "Real" / "Static" tag
// ============================================================

import type { DataSource } from "../../types";

interface DataSourceBadgeProps {
  source: DataSource | "Static" | "Unavailable";
  className?: string;
}

const CONFIG: Record<
  string,
  { label: string; dot: string; text: string; border: string }
> = {
  real: {
    label: "Real",
    dot: "bg-green-400",
    text: "text-green-400",
    border: "border-green-500/30",
  },
  sample: {
    label: "Sample",
    dot: "bg-amber-400",
    text: "text-amber-400",
    border: "border-amber-500/30",
  },
  Static: {
    label: "Static",
    dot: "bg-slate-400",
    text: "text-slate-400",
    border: "border-slate-500/30",
  },
  unavailable: {
    label: "N/A",
    dot: "bg-slate-600",
    text: "text-slate-500",
    border: "border-slate-600/30",
  },
  Unavailable: {
    label: "N/A",
    dot: "bg-slate-600",
    text: "text-slate-500",
    border: "border-slate-600/30",
  },
};

export default function DataSourceBadge({
  source,
  className = "",
}: DataSourceBadgeProps) {
  const cfg = CONFIG[source] ?? CONFIG.unavailable;
  return (
    <span
      className={`source-badge bg-slate-900/60 border ${cfg.border} ${cfg.text} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}
