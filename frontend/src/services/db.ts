import { openDB, type DBSchema, type IDBPDatabase } from "idb";
import { submitFieldReport } from "./api";

interface FieldReportDB extends DBSchema {
  reports: {
    key: string;
    value: {
      id: string;
      timestamp: string;
      lat: number;
      lon: number;
      zone_id?: string;
      category: string;
      severity: string;
      description: string;
      reporter?: string;
      photo_base64?: string;
      photo_status?: "QUEUED" | "SYNCED";
      sync_status: "LOCAL_ONLY" | "SYNC_PENDING" | "SYNCING" | "SYNCED" | "SYNC_FAILED";
    };
  };
}

let dbPromise: Promise<IDBPDatabase<FieldReportDB>> | null = null;

export function getDB() {
  if (!dbPromise) {
    dbPromise = openDB<FieldReportDB>("terrasense-db", 1, {
      upgrade(db) {
        db.createObjectStore("reports", { keyPath: "id" });
      },
    });
  }
  return dbPromise;
}

export async function saveReportLocally(report: any) {
  const db = await getDB();
  await db.put("reports", report);
}

export async function getLocalReports() {
  const db = await getDB();
  return await db.getAll("reports");
}

export async function syncPendingReports() {
  const db = await getDB();
  const all = await db.getAll("reports");
  
  const pending = all.filter(r => r.sync_status === "LOCAL_ONLY" || r.sync_status === "SYNC_PENDING" || r.sync_status === "SYNC_FAILED");
  
  if (pending.length === 0) return 0;
  
  let synced = 0;
  for (const report of pending) {
    try {
      report.sync_status = "SYNCING";
      await db.put("reports", report);
      
      const saved = await submitFieldReport(report);
      
      // Update with server response
      saved.sync_status = "SYNCED";
      await db.put("reports", saved);
      synced++;
    } catch (err) {
      console.error("Failed to sync report", report.id, err);
      report.sync_status = "SYNC_FAILED";
      await db.put("reports", report);
    }
  }
  return synced;
}

// Auto-sync listener
if (typeof window !== "undefined") {
  window.addEventListener("online", () => {
    syncPendingReports().catch(console.error);
  });
}
