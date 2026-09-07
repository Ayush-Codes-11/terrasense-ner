import { Link } from "react-router-dom";
import type { DistrictMeta } from "../../types";
import { formatDateTime } from "../../utils/risk";

interface TopBarProps {
  districtMeta?: DistrictMeta | null;
  lastUpdated?: string | null;
  isOffline?: boolean;
}

export default function TopBar({ districtMeta, lastUpdated, isOffline }: TopBarProps) {
  return (
    <header className="flex items-center justify-between px-4 py-2 bg-[#07111F] border-b border-slate-800 shrink-0 z-10">
      {/* Left: Logo + District */}
      <div className="flex items-center gap-4">
        <Link to="/" className="flex items-center gap-2 group">
          {/* Logo mark */}
          <div className="w-7 h-7 rounded bg-[#22D3EE]/20 flex items-center justify-center shrink-0 border border-[#22D3EE]/30">
            <svg
              className="w-4 h-4 text-[#22D3EE]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
              />
            </svg>
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 leading-tight group-hover:text-[#22D3EE] transition-colors">
              TerraSense NER
            </div>
            <div className="text-[10px] text-slate-500 leading-tight uppercase tracking-wide">
              Landslide Early Warning
            </div>
          </div>
        </Link>

        <div className="h-5 w-px bg-slate-800" />

        {/* Pilot district */}
        <div className="flex items-center gap-3">
          <div>
            <div className="text-[9px] text-[#22D3EE] font-semibold uppercase tracking-widest">Pilot Deployment</div>
            <div className="text-xs font-medium text-slate-300">
              {districtMeta?.district_name ?? "Aizawl"},{" "}
              {districtMeta?.state ?? "Mizoram"}
            </div>
          </div>
        </div>
      </div>

      {/* Right: Timestamp */}
      <div className="flex items-center gap-3">
        <div className="hidden md:block text-right">
          <div className="text-[9px] text-slate-500 uppercase tracking-widest">
            {isOffline ? "Last valid update" : "Last updated"}
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            {lastUpdated
              ? formatDateTime(lastUpdated)
              : districtMeta?.last_updated
                ? formatDateTime(districtMeta.last_updated)
                : "—"}
          </div>
        </div>
      </div>
    </header>
  );
}
