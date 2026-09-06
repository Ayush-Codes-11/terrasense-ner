import { Link, useLocation } from "react-router-dom";
import type { DistrictMeta } from "../../types";
import { formatDateTime } from "../../utils/risk";

interface TopBarProps {
  districtMeta?: DistrictMeta | null;
}

export default function TopBar({ districtMeta }: TopBarProps) {
  const location = useLocation();
  const isFieldReport = location.pathname === "/field-report";

  return (
    <header className="flex items-center justify-between px-4 py-2.5 bg-slate-900 border-b border-slate-700 shrink-0 z-10">
      {/* Left: Logo + District */}
      <div className="flex items-center gap-4">
        <Link to="/" className="flex items-center gap-2 group">
          {/* Logo mark */}
          <div className="w-8 h-8 rounded-md bg-blue-600 flex items-center justify-center shrink-0">
            <svg
              className="w-5 h-5 text-white"
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
            <div className="text-sm font-bold text-white leading-tight group-hover:text-blue-400 transition-colors">
              TerraSense NER
            </div>
            <div className="text-[10px] text-slate-400 leading-tight">
              Landslide Early Warning
            </div>
          </div>
        </Link>

        <div className="h-6 w-px bg-slate-700" />

        {/* Pilot district */}
        <div className="flex items-center gap-4">
          <div>
            <div className="text-[10px] text-amber-400 font-semibold uppercase tracking-wider">Pilot</div>
            <div className="text-sm font-medium text-white">
              {districtMeta?.district_name ?? "Aizawl"},{" "}
              {districtMeta?.state ?? "Mizoram"}
            </div>
          </div>
          <div className="h-6 w-px bg-slate-700 hidden sm:block" />
          <div className="hidden sm:block">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">Designed Scope</div>
            <div className="text-xs font-medium text-slate-300">
              North Eastern Region
            </div>
          </div>
        </div>
      </div>

      {/* Centre removed per Phase 12 clean visual rules */}

      {/* Right: Timestamp + Nav */}
      <div className="flex items-center gap-3">
        <div className="hidden md:block text-right">
          <div className="text-[10px] text-slate-500">Last updated</div>
          <div className="text-xs text-slate-300">
            {districtMeta?.last_updated
              ? formatDateTime(districtMeta.last_updated)
              : "—"}
          </div>
        </div>

        <div className="h-6 w-px bg-slate-700" />

        {isFieldReport ? (
          <Link
            to="/"
            className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-white transition-colors px-2 py-1 rounded hover:bg-slate-800"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Dashboard
          </Link>
        ) : (
          <Link
            to="/field-report"
            className="flex items-center gap-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded transition-colors font-medium"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            File Report
          </Link>
        )}
      </div>
    </header>
  );
}
