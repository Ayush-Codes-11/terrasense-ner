// ============================================================
// Risk utility helpers — colour, label, icon
// ============================================================

import type { RiskLevel } from "../types";

export const RISK_COLORS: Record<RiskLevel, string> = {
  LOW: "#22c55e",
  MODERATE: "#eab308",
  HIGH: "#f97316",
  VERY_HIGH: "#ef4444",
};

export const RISK_BG_CLASSES: Record<RiskLevel, string> = {
  LOW: "bg-green-500/20 text-green-400 border-green-500/40",
  MODERATE: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
  HIGH: "bg-orange-500/20 text-orange-400 border-orange-500/40",
  VERY_HIGH: "bg-red-500/20 text-red-400 border-red-500/40",
};

export const RISK_LABEL: Record<RiskLevel, string> = {
  LOW: "Low",
  MODERATE: "Moderate",
  HIGH: "High",
  VERY_HIGH: "Very High",
};

export const PRIORITY_BG_CLASSES: Record<string, string> = {
  LOW: "bg-slate-500/20 text-slate-400 border-slate-500/40",
  MODERATE: "bg-blue-500/20 text-blue-400 border-blue-500/40",
  MEDIUM: "bg-blue-500/20 text-blue-400 border-blue-500/40",
  HIGH: "bg-orange-500/20 text-orange-400 border-orange-500/40",
  VERY_HIGH: "bg-red-500/20 text-red-400 border-red-500/40",
  CRITICAL: "bg-red-500/20 text-red-400 border-red-500/40",
};

export function riskFromScore(score: number): RiskLevel {
  if (score < 0.25) return "LOW";
  if (score < 0.5) return "MODERATE";
  if (score < 0.75) return "HIGH";
  return "VERY_HIGH";
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
