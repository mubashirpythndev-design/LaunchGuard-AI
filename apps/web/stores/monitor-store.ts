import { create } from "zustand";
import type { FindingSchema, MonitorLogEntry } from "@launchguard/contract";

export type MonitorSource = "image" | "video" | "webcam";
export type ZoneStatus = "CLEAR" | "WARNING" | "DANGER";
export type Point2D = [number, number];

export interface MonitorState {
  runId: string | null;
  source: MonitorSource;
  zonePoints: Point2D[];
  zoneLabel: string;
  isZoneEditing: boolean;
  liveStatus: ZoneStatus;
  isMonitoring: boolean;
  isStale: boolean;
  processingMs: number;
  fps: number;
  findings: FindingSchema[];
  logs: MonitorLogEntry[];
  validationError: string | null;

  // Actions
  setRunId: (id: string | null) => void;
  setSource: (source: MonitorSource) => void;
  setZonePoints: (points: Point2D[]) => void;
  addZonePoint: (point: Point2D) => void;
  updateZonePoint: (index: number, point: Point2D) => void;
  clearZonePoints: () => void;
  setZoneLabel: (label: string) => void;
  setIsZoneEditing: (editing: boolean) => void;
  setLiveStatus: (status: ZoneStatus) => void;
  setIsMonitoring: (monitoring: boolean) => void;
  setIsStale: (stale: boolean) => void;
  setProcessingMs: (ms: number) => void;
  setFps: (fps: number) => void;
  setFindings: (findings: FindingSchema[]) => void;
  addLogEntry: (entry: MonitorLogEntry) => void;
  setValidationError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  runId: null,
  source: "webcam" as MonitorSource,
  zonePoints: [] as Point2D[],
  zoneLabel: "Pad Danger Exclusion Zone",
  isZoneEditing: false,
  liveStatus: "CLEAR" as ZoneStatus,
  isMonitoring: false,
  isStale: false,
  processingMs: 0,
  fps: 0,
  findings: [] as FindingSchema[],
  logs: [] as MonitorLogEntry[],
  validationError: null as string | null,
};

export const useMonitorStore = create<MonitorState>((set) => ({
  ...initialState,

  setRunId: (runId) => set({ runId }),
  setSource: (source) => set({ source }),
  setZonePoints: (zonePoints) => set({ zonePoints, validationError: null }),
  addZonePoint: (point) =>
    set((state) => ({
      zonePoints: [...state.zonePoints, point],
      validationError: null,
    })),
  updateZonePoint: (index, point) =>
    set((state) => {
      const updated = [...state.zonePoints];
      if (index >= 0 && index < updated.length) {
        updated[index] = point;
      }
      return { zonePoints: updated, validationError: null };
    }),
  clearZonePoints: () => set({ zonePoints: [], validationError: null }),
  setZoneLabel: (zoneLabel) => set({ zoneLabel }),
  setIsZoneEditing: (isZoneEditing) => set({ isZoneEditing }),
  setLiveStatus: (liveStatus) => set({ liveStatus }),
  setIsMonitoring: (isMonitoring) => set({ isMonitoring }),
  setIsStale: (isStale) => set({ isStale }),
  setProcessingMs: (processingMs) => set({ processingMs }),
  setFps: (fps) => set({ fps }),
  setFindings: (findings) => set({ findings }),
  addLogEntry: (entry) =>
    set((state) => ({
      logs: [entry, ...state.logs].slice(0, 50),
    })),
  setValidationError: (validationError) => set({ validationError }),
  reset: () => set(initialState),
}));
