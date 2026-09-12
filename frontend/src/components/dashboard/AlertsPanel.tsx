import { useState, useEffect } from "react";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [backendAvailable, setBackendAvailable] = useState<boolean | null>(null);
  const [permission, setPermission] = useState<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "default"
  );

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      const res = await fetch(`${API_BASE}/alerts`);
      if (res.ok) {
        setAlerts(await res.json());
        setBackendAvailable(true);
      } else {
        setBackendAvailable(false);
      }
    } catch {
      setBackendAvailable(false);
    }
  };

  const requestPermission = async () => {
    if (typeof Notification !== "undefined") {
      const perm = await Notification.requestPermission();
      setPermission(perm);
    }
  };

  const sendTestAlert = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/alerts/test`, { method: "POST" });
      if (res.ok) {
        const newAlert = await res.json();
        setAlerts((prev) => [newAlert, ...prev]);
        setBackendAvailable(true);
        
        // Show browser notification if allowed
        if (permission === "granted") {
          new Notification("TerraSense Prototype Alert", {
            body: `Zone ${newAlert.zone_id}: VERY HIGH priority at +24h.\n${newAlert.rationale}`,
            icon: "/icon-192.png",
          });
        }
      }
    } catch {
      setBackendAvailable(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-3 flex flex-col gap-2 h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
          ALERTS
        </h2>
        {permission !== "granted" ? (
          <button 
            onClick={requestPermission}
            className="text-[10px] bg-slate-700 hover:bg-slate-600 text-slate-300 px-2 py-1 rounded transition-colors"
          >
            Enable Notifications
          </button>
        ) : (
          <span className="text-[10px] text-green-400 border border-green-500/30 bg-green-500/10 px-1.5 py-0.5 rounded">
            Local PWA Notification Enabled
          </span>
        )}
      </div>
      {backendAvailable === false && (
        <p className="text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-1.5">
          Backend offline. Browser notifications remain local; no alert was sent.
        </p>
      )}

      <button
        onClick={sendTestAlert}
        disabled={loading}
        className="w-full py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-600 transition-colors"
      >
        {loading ? "Sending..." : "Preview Test Alert"}
      </button>

      {alerts.length > 0 && (
        <div className="flex flex-col gap-2 mt-2 pb-10">
          {alerts.map((a) => (
            <div key={a.alert_id} className="p-3 rounded bg-[#07111F]/80 border-l-[3px] border-l-red-500 border border-t-slate-700/30 border-r-slate-700/30 border-b-slate-700/30 flex flex-col gap-1.5 shadow-sm">
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs font-bold text-slate-100 uppercase leading-tight">VERY HIGH<br/><span className="text-[#94A3B8] font-medium">Zone {a.zone_id}</span></span>
                <span className="text-[10px] text-slate-500 font-mono whitespace-nowrap">{new Date(a.created_at).toLocaleTimeString()}</span>
              </div>
              <p className="text-[11px] text-slate-300 leading-snug">{a.rationale}</p>
              <div className="flex items-center justify-between mt-1 pt-1.5 border-t border-slate-800/80">
                <span className="text-[9px] text-slate-500 uppercase tracking-widest">Channels: {a.delivery_channels.join(", ")}</span>
                <span className="text-[9px] font-bold text-amber-500 uppercase">{a.delivery_status}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
