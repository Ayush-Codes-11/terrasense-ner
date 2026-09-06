import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import TopBar from "../components/layout/TopBar";
import type { ReportType } from "../types";
import { saveReportLocally, syncPendingReports } from "../services/db";

const REPORT_TYPES: { value: ReportType; label: string; icon: string; desc: string }[] = [
  {
    value: "slope_crack",
    label: "Slope Crack",
    icon: "🪨",
    desc: "Visible cracks or movement on hillside",
  },
  {
    value: "debris",
    label: "Debris / Rockfall",
    icon: "⛰",
    desc: "Fallen rocks, soil, or debris on road/land",
  },
  {
    value: "road_blockage",
    label: "Road Blockage",
    icon: "🚧",
    desc: "Road partially or fully obstructed",
  },
  {
    value: "landslide",
    label: "Active Landslide",
    icon: "⚠️",
    desc: "Active slope failure or landslide in progress",
  },
  {
    value: "other",
    label: "Other",
    icon: "📍",
    desc: "Other hazard or observation",
  },
];

export default function FieldReport() {
  const navigate = useNavigate();
  const [selectedType, setSelectedType] = useState<ReportType | null>(null);
  const [description, setDescription] = useState("");
  const [blockedRoad, setBlockedRoad] = useState(false);
  const [reporter, setReporter] = useState("");
  const [zoneId, setZoneId] = useState("C03");
  const [severity, setSeverity] = useState("MODERATE");
  
  const [lat, setLat] = useState<number | null>(null);
  const [lon, setLon] = useState<number | null>(null);
  
  const [submitting, setSubmitting] = useState(false);

  const isPhase8 = true; // Enabled in Phase 8

  const detectLocation = () => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLat(Number(pos.coords.latitude.toFixed(6)));
          setLon(Number(pos.coords.longitude.toFixed(6)));
        },
        (err) => alert(`GPS Error: ${err.message}`)
      );
    } else {
      alert("Geolocation is not supported by your browser");
    }
  };

  const handleSubmit = async () => {
    if (!selectedType || lat === null || lon === null || !reporter) {
      alert("Please fill in all required fields (Type, GPS, Reporter)");
      return;
    }

    setSubmitting(true);
    const report = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      lat,
      lon,
      zone_id: zoneId || undefined,
      category: selectedType,
      severity,
      description: description + (selectedType === "road_blockage" && blockedRoad ? " [ROAD CONFIRMED BLOCKED]" : ""),
      reporter: reporter || undefined,
      sync_status: navigator.onLine ? "SYNC_PENDING" : "LOCAL_ONLY",
    };

    try {
      // 1. Save locally to IndexedDB immediately
      await saveReportLocally(report);
      
      // 2. Try to sync immediately if online
      if (navigator.onLine) {
        await syncPendingReports();
      }
      
      alert("Report submitted successfully and synced with backend!");
    } catch (err) {
      console.warn("Backend sync failed, saved locally", err);
      alert("Report saved locally. Backend sync failed (SYNC PENDING).");
    }

    setSubmitting(false);
    navigate("/");
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-900">
      <TopBar districtMeta={null} />

      <main className="flex-1 max-w-lg mx-auto w-full px-4 py-6">
        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-lg font-bold text-white">Submit Field Report</h1>
          <p className="text-sm text-slate-400 mt-1">
            Report hazards, slope movement, or road conditions in Aizawl
            District.
          </p>
        </div>

        <div className="flex flex-col gap-5">
          {/* Reporter details */}
          <div className="card p-4">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
              Reporter Details
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wide">
                  Name
                </label>
                <input
                  type="text"
                  value={reporter}
                  onChange={(e) => setReporter(e.target.value)}
                  placeholder="Your name"
                  className="w-full mt-1 px-2 py-1.5 rounded bg-slate-900 border border-slate-700 text-xs text-slate-300 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wide">
                  Zone ID (optional)
                </label>
                <input
                  type="text"
                  value={zoneId}
                  onChange={(e) => setZoneId(e.target.value)}
                  placeholder="e.g. C03"
                  className="w-full mt-1 px-2 py-1.5 rounded bg-slate-900 border border-slate-700 text-xs text-slate-300 focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* GPS Location */}
          <div className="card p-4">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
              📍 Location
            </h2>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-300">GPS Coordinates</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Tap to detect location
                </p>
              </div>
              <button
                onClick={detectLocation}
                disabled={!isPhase8}
                className="px-3 py-1.5 rounded-md text-xs font-medium transition-colors bg-blue-600 hover:bg-blue-500 text-white"
              >
                Detect GPS
              </button>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wide">
                  Latitude
                </label>
                <input
                  type="text"
                  readOnly
                  value={lat ?? ""}
                  placeholder="—"
                  className="w-full mt-1 px-2 py-1.5 rounded bg-slate-900 border border-slate-700 text-xs text-slate-500"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wide">
                  Longitude
                </label>
                <input
                  type="text"
                  readOnly
                  value={lon ?? ""}
                  placeholder="—"
                  className="w-full mt-1 px-2 py-1.5 rounded bg-slate-900 border border-slate-700 text-xs text-slate-500"
                />
              </div>
            </div>
          </div>

          {/* Report type */}
          <div className="card p-4">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
              Report Type
            </h2>
            <div className="flex flex-col gap-2">
              {REPORT_TYPES.map((t) => (
                <label
                  key={t.value}
                  className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedType === t.value
                      ? "bg-blue-600/10 border-blue-500/50"
                      : "bg-slate-900/40 border-slate-700/50 hover:border-slate-600"
                  }`}
                >
                  <input
                    type="radio"
                    name="report_type"
                    value={t.value}
                    checked={selectedType === t.value}
                    onChange={() => setSelectedType(t.value)}
                    className="accent-blue-500"
                  />
                  <span className="text-lg shrink-0">{t.icon}</span>
                  <div>
                    <p className="text-sm font-medium text-slate-200">
                      {t.label}
                    </p>
                    <p className="text-[11px] text-slate-500">{t.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Severity */}
          <div className="card p-4">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
              Severity
            </h2>
            <select 
              value={severity} 
              onChange={(e) => setSeverity(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-sm text-slate-300 focus:outline-none focus:border-blue-500/60"
            >
              <option value="LOW">Low - Observation only</option>
              <option value="MODERATE">Moderate - Needs attention</option>
              <option value="HIGH">High - Immediate hazard</option>
              <option value="CRITICAL">Critical - Life-threatening / Blocked completely</option>
            </select>
          </div>

          {/* Road blocked toggle (only shown for road_blockage type) */}
          {selectedType === "road_blockage" && (
            <div className="card p-4">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
                🚧 Blockage Status
              </h2>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={blockedRoad}
                  onChange={(e) => setBlockedRoad(e.target.checked)}
                  className="w-4 h-4 accent-red-500"
                />
                <div>
                  <p className="text-sm text-slate-300 font-medium">
                    Road is confirmed blocked
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Only check if you have personally verified the blockage. This
                    will mark the road as blocked on the map.
                  </p>
                </div>
              </label>
            </div>
          )}

          {/* Photo upload */}
          <div className="card p-4">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
              📷 Photo (optional)
            </h2>
            <div
              className={`flex flex-col items-center justify-center gap-2 p-6 rounded-lg border-2 border-dashed border-slate-600 cursor-pointer hover:border-slate-500 transition-colors`}
            >
              <span className="text-2xl opacity-40">📷</span>
              <p className="text-xs text-slate-500">
                Tap to capture or upload photo
              </p>
            </div>
          </div>

          {/* Description */}
          <div className="card p-4">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
              Description
            </h2>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what you observed — location details, severity, any immediate danger..."
              rows={4}
              className="w-full px-3 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500/60 resize-none transition-colors"
            />
          </div>

          {/* Submit */}
          <div className="flex flex-col gap-2">
            <button
              onClick={handleSubmit}
              disabled={!selectedType || submitting}
              className={`w-full py-3 rounded-lg font-semibold text-sm transition-all ${
                !selectedType || submitting
                  ? "bg-slate-700 text-slate-500 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-500 text-white active:scale-[0.98]"
              }`}
            >
              {submitting ? "Submitting..." : "Submit Report"}
            </button>
            <Link
              to="/"
              className="text-center text-xs text-slate-500 hover:text-slate-400 transition-colors py-2"
            >
              ← Back to dashboard
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
