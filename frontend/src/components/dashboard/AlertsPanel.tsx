import { useState, useEffect } from "react";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
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
      }
    } catch (e) {
      console.error(e);
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
        
        // Show browser notification if allowed
        if (permission === "granted") {
          new Notification("TerraSense Prototype Alert", {
            body: `Zone ${newAlert.zone_id}: VERY HIGH priority at +24h.\n${newAlert.rationale}`,
            icon: "/icon-192.png",
          });
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
          Alert Engine (Phase 11)
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

      <button
        onClick={sendTestAlert}
        disabled={loading}
        className="w-full py-1.5 rounded bg-red-600/20 hover:bg-red-600/30 text-red-400 text-xs font-medium border border-red-500/30 transition-colors"
      >
        {loading ? "Sending..." : "Send Test Alert (SMS Preview)"}
      </button>

      {alerts.length > 0 && (
        <div className="flex flex-col gap-2 mt-1 max-h-48 overflow-y-auto pr-1">
          {alerts.map((a) => (
            <div key={a.alert_id} className="p-2 rounded bg-slate-900 border border-slate-700/50 flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-red-400">Zone {a.zone_id} ALERT</span>
                <span className="text-[9px] text-slate-500">{new Date(a.created_at).toLocaleTimeString()}</span>
              </div>
              <p className="text-[10px] text-slate-300">{a.rationale}</p>
              <div className="flex items-center justify-between mt-1 pt-1 border-t border-slate-800">
                <span className="text-[9px] text-slate-500">Channels: {a.delivery_channels.join(", ")}</span>
                <span className="text-[9px] font-medium text-amber-500">{a.delivery_status}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
