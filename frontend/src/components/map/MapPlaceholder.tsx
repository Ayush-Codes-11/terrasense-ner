// ============================================================
// MapPlaceholder — Phase 1 only
// Phase 2 replaces this entirely with RiskMap.tsx (Leaflet)
// DO NOT add Leaflet or GeoJSON here.
// ============================================================

interface MapPlaceholderProps {
  onZoneSelect?: (zoneId: string) => void;
}

export default function MapPlaceholder({ onZoneSelect }: MapPlaceholderProps) {
  // Demo zone grid to make the placeholder interactive
  const demoZones = [
    { id: "A01", label: "Zone A01", top: "15%", left: "18%", risk: "LOW" },
    { id: "A02", label: "Zone A02", top: "22%", left: "38%", risk: "MODERATE" },
    { id: "A03", label: "Zone A03", top: "15%", left: "57%", risk: "HIGH" },
    { id: "B01", label: "Zone B01", top: "38%", left: "18%", risk: "MODERATE" },
    { id: "B02", label: "Zone B02", top: "38%", left: "38%", risk: "HIGH" },
    { id: "B03", label: "Zone B03", top: "38%", left: "57%", risk: "VERY_HIGH" },
    { id: "C01", label: "Zone C01", top: "58%", left: "18%", risk: "LOW" },
    { id: "C02", label: "Zone C02", top: "58%", left: "38%", risk: "MODERATE" },
    { id: "C03", label: "Zone C03", top: "58%", left: "57%", risk: "HIGH" },
  ] as const;

  const riskColor: Record<string, string> = {
    LOW: "#22c55e",
    MODERATE: "#eab308",
    HIGH: "#f97316",
    VERY_HIGH: "#ef4444",
  };

  return (
    <div className="relative w-full h-full bg-slate-950 rounded-lg overflow-hidden border border-slate-700 flex flex-col">
      {/* Placeholder header */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-900 border-b border-slate-700 shrink-0">
        <span className="text-xs text-slate-400 font-medium">
          GIS Map — Aizawl District, Mizoram
        </span>
        <span className="text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded font-medium">
          Map placeholder · Phase 2 will render real Leaflet/GeoJSON
        </span>
      </div>

      {/* Fake terrain background */}
      <div className="relative flex-1 overflow-hidden">
        {/* Terrain texture gradient */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse at 30% 40%, #1e293b 0%, #0f172a 60%, #020617 100%)",
          }}
        />
        {/* Grid lines */}
        <svg
          className="absolute inset-0 w-full h-full opacity-10"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
              <path
                d="M 60 0 L 0 0 0 60"
                fill="none"
                stroke="#94a3b8"
                strokeWidth="0.5"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>

        {/* Simulated contour lines */}
        <svg
          className="absolute inset-0 w-full h-full opacity-[0.07]"
          viewBox="0 0 800 500"
          preserveAspectRatio="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M 50 200 Q 200 150 350 180 Q 500 210 650 170 Q 750 150 800 200"
            fill="none"
            stroke="#60a5fa"
            strokeWidth="2"
          />
          <path
            d="M 30 280 Q 180 240 330 260 Q 480 290 630 250 Q 720 230 800 280"
            fill="none"
            stroke="#60a5fa"
            strokeWidth="2"
          />
          <path
            d="M 10 360 Q 160 330 310 350 Q 460 370 610 340 Q 700 320 800 360"
            fill="none"
            stroke="#60a5fa"
            strokeWidth="2"
          />
          <path
            d="M 100 120 Q 250 90 400 110 Q 550 135 700 100"
            fill="none"
            stroke="#60a5fa"
            strokeWidth="1.5"
          />
        </svg>

        {/* Simulated river */}
        <svg
          className="absolute inset-0 w-full h-full opacity-20"
          viewBox="0 0 800 500"
          preserveAspectRatio="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M 400 50 Q 420 100 410 150 Q 395 200 415 250 Q 435 300 420 360 Q 405 420 430 480"
            fill="none"
            stroke="#38bdf8"
            strokeWidth="3"
          />
        </svg>

        {/* Risk zone overlays */}
        {demoZones.map((zone) => (
          <button
            key={zone.id}
            className="absolute w-24 h-16 rounded border-2 transition-all duration-150 hover:scale-105 hover:z-10 flex items-center justify-center cursor-pointer"
            style={{
              top: zone.top,
              left: zone.left,
              backgroundColor: riskColor[zone.risk] + "30",
              borderColor: riskColor[zone.risk] + "80",
              transform: "translate(-50%, -50%)",
            }}
            onClick={() => onZoneSelect?.(zone.id)}
            title={`${zone.label} — ${zone.risk.replace("_", " ")}`}
          >
            <div className="text-center">
              <div className="text-[10px] font-bold text-white/70">{zone.id}</div>
              <div
                className="text-[9px] font-semibold"
                style={{ color: riskColor[zone.risk] }}
              >
                {zone.risk.replace("_", " ")}
              </div>
            </div>
          </button>
        ))}

        {/* Compass rose */}
        <div className="absolute top-3 right-3 w-8 h-8 opacity-30">
          <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="16" cy="16" r="14" stroke="#94a3b8" strokeWidth="1" />
            <path d="M16 4 L18 14 L16 13 L14 14 Z" fill="#f8fafc" />
            <path d="M16 28 L18 18 L16 19 L14 18 Z" fill="#64748b" />
            <path d="M4 16 L14 14 L13 16 L14 18 Z" fill="#64748b" />
            <path d="M28 16 L18 14 L19 16 L18 18 Z" fill="#64748b" />
            <text x="16" y="7" textAnchor="middle" fontSize="4" fill="#f8fafc" fontWeight="bold">N</text>
          </svg>
        </div>

        {/* Scale bar placeholder */}
        <div className="absolute bottom-3 left-3 flex items-center gap-1 opacity-40">
          <div className="w-12 h-1 bg-slate-400" />
          <span className="text-[9px] text-slate-400">~2 km</span>
        </div>

        <div className="absolute bottom-1 right-2 text-[9px] text-slate-600">
          Sample visualization - georeferenced prototype boundaries
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 px-3 py-2 bg-slate-900 border-t border-slate-700 shrink-0">
        <span className="text-[10px] text-slate-500 uppercase tracking-wide">
          Risk
        </span>
        {(["LOW", "MODERATE", "HIGH", "VERY_HIGH"] as const).map((r) => (
          <div key={r} className="flex items-center gap-1">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: riskColor[r] }}
            />
            <span className="text-[10px] text-slate-400">
              {r.replace("_", " ")}
            </span>
          </div>
        ))}
        <span className="ml-auto text-[10px] text-slate-600 italic">
          Click a zone to see details
        </span>
      </div>
    </div>
  );
}
