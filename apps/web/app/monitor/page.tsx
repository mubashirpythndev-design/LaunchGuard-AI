"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Play,
  Square,
  AlertCircle,
  Video,
  Eye,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { SourceSelector } from "@/components/monitor/SourceSelector";
import { ZoneEditor } from "@/components/monitor/ZoneEditor";
import { LiveStatusBanner } from "@/components/monitor/LiveStatusBanner";
import { Disclaimer } from "@/components/verdict/Disclaimer";
import { useWebcam } from "@/hooks/use-webcam";
import { useMonitorStore, type Point2D } from "@/stores/monitor-store";
import type { CreateRunResponse, FrameAnalysisResponse } from "@/lib/schemas";

export default function MonitorPage() {
  const {
    runId,
    source,
    zonePoints,
    isMonitoring,
    isZoneEditing,
    setRunId,
    setIsMonitoring,
    setLiveStatus,
    setProcessingMs,
    setFindings,
    addLogEntry,
    setValidationError,
  } = useMonitorStore();

  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState<boolean>(false);
  const [pageError, setPageError] = useState<string | null>(null);

  const videoElementRef = useRef<HTMLVideoElement | null>(null);
  const { videoRef, startStream, stopStream } = useWebcam({ frameRate: 5 });

  // Initialize a monitor run session on the server if not already created
  const initRun = useCallback(async (): Promise<string | null> => {
    try {
      setIsInitializing(true);
      setPageError(null);
      const res = await fetch("/api/monitor", { method: "POST" });
      if (!res.ok) {
        throw new Error("Failed to initialize monitor run session.");
      }
      const data: CreateRunResponse = await res.json();
      setRunId(data.run_id);
      return data.run_id;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error creating monitor run.";
      setPageError(msg);
      return null;
    } finally {
      setIsInitializing(false);
    }
  }, [setRunId]);

  useEffect(() => {
    if (!runId) {
      void initRun();
    }
  }, [runId, initRun]);

  // Handle source switching
  useEffect(() => {
    if (source === "webcam") {
      void startStream();
    } else {
      stopStream();
    }
  }, [source, startStream, stopStream]);

  // Save danger zone to backend API
  const handleSaveZone = async (points: Point2D[]) => {
    let activeRunId = runId;
    if (!activeRunId) {
      activeRunId = await initRun();
      if (!activeRunId) return;
    }

    try {
      setPageError(null);
      const res = await fetch(`/api/monitor/${activeRunId}/zone`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          points,
          label: "Pad Danger Exclusion Zone",
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.error?.message || "Failed to save danger zone.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error saving danger zone";
      setValidationError(msg);
    }
  };

  // Image source file selection
  const handleImageSelected = (file: File) => {
    const url = URL.createObjectURL(file);
    setImageSrc(url);
    setIsMonitoring(false);
  };

  // Video source file selection
  const handleVideoSelected = (file: File) => {
    const url = URL.createObjectURL(file);
    setVideoSrc(url);
    setIsMonitoring(false);
  };

  // Analyze single static image frame
  const handleAnalyzeStaticImage = async () => {
    if (!runId || !imageSrc) return;
    if (zonePoints.length < 3) {
      setValidationError("Please draw and save a danger zone before analyzing.");
      return;
    }

    try {
      setPageError(null);
      const blobRes = await fetch(imageSrc);
      const blob = await blobRes.blob();

      const startTime = performance.now();
      const res = await fetch(`/api/monitor/${runId}/frame`, {
        method: "POST",
        headers: { "Content-Type": "image/jpeg" },
        body: blob,
      });

      if (res.status === 409) {
        setValidationError("Danger zone not recognized on server. Please save zone again.");
        return;
      }

      if (!res.ok) {
        throw new Error("Failed to process static frame.");
      }

      const data: FrameAnalysisResponse = await res.json();
      const elapsed = Math.round(performance.now() - startTime);

      setProcessingMs(data.processing_ms || elapsed);
      setLiveStatus(data.zone_status as "CLEAR" | "WARNING" | "DANGER");
      setFindings(data.findings || []);
      addLogEntry({
        at: new Date().toISOString(),
        zone_status: data.zone_status,
        check_ids: data.findings ? data.findings.map((f) => f.check_id) : [],
        max_severity:
          data.zone_status === "DANGER"
            ? "critical"
            : data.zone_status === "WARNING"
              ? "warning"
              : "ok",
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error analyzing frame.";
      setPageError(msg);
    }
  };

  // Toggle monitoring state
  const handleToggleMonitoring = () => {
    if (zonePoints.length < 3) {
      setValidationError("A danger zone must contain at least 3 points before starting monitoring.");
      return;
    }
    setValidationError(null);
    setIsMonitoring(!isMonitoring);
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col justify-between">
      {/* Top Navigation */}
      <header className="border-b border-border bg-card px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Dashboard</span>
          </Link>
          <div className="h-4 w-px bg-border" />
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-steel" />
            <h1 className="text-sm font-semibold tracking-tight uppercase">
              Launchpad Danger Zone Monitor
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {runId && (
            <span className="text-xs font-mono text-muted-foreground">
              Run: {runId.slice(0, 8)}...
            </span>
          )}
          <Button
            size="sm"
            variant={isMonitoring ? "destructive" : "default"}
            disabled={isInitializing || isZoneEditing}
            onClick={handleToggleMonitoring}
            data-testid="toggle-monitoring-btn"
            className="flex items-center gap-1.5"
          >
            {isMonitoring ? (
              <>
                <Square className="w-3.5 h-3.5" />
                <span>Stop Monitor</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" />
                <span>Start Monitor</span>
              </>
            )}
          </Button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Media viewport & polygon editor (2 cols wide) */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          {pageError && (
            <div
              role="alert"
              className="flex items-center gap-2 p-3 rounded-md bg-destructive/10 border border-destructive text-destructive text-xs"
            >
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{pageError}</span>
            </div>
          )}

          <ZoneEditor onSaveZone={handleSaveZone}>
            {/* Webcam Live Feed */}
            {source === "webcam" && (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                data-testid="webcam-feed"
                className="w-full h-full object-cover"
              />
            )}

            {/* Video File Feed */}
            {source === "video" && (
              videoSrc ? (
                <video
                  ref={videoElementRef}
                  src={videoSrc}
                  controls
                  playsInline
                  data-testid="video-feed"
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex flex-col items-center justify-center gap-2 text-muted-foreground">
                  <Video className="w-8 h-8 opacity-40" />
                  <span className="text-xs">No video loaded. Select a file below.</span>
                </div>
              )
            )}

            {/* Static Image Frame Feed */}
            {source === "image" && (
              imageSrc ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={imageSrc}
                  alt="Static frame preview"
                  data-testid="image-feed"
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex flex-col items-center justify-center gap-2 text-muted-foreground">
                  <Eye className="w-8 h-8 opacity-40" />
                  <span className="text-xs">No frame loaded. Select an image below.</span>
                </div>
              )
            )}
          </ZoneEditor>

          {/* Action triggers for static image testing */}
          {source === "image" && imageSrc && (
            <div className="flex justify-end">
              <Button
                size="sm"
                onClick={handleAnalyzeStaticImage}
                disabled={zonePoints.length < 3}
                data-testid="analyze-frame-btn"
                className="flex items-center gap-1.5"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Evaluate Frame Clearance</span>
              </Button>
            </div>
          )}
        </div>

        {/* Right Column: Controls, Telemetry, and Live Status (1 col) */}
        <div className="flex flex-col gap-4">
          <LiveStatusBanner />
          <SourceSelector
            onImageSelected={handleImageSelected}
            onVideoSelected={handleVideoSelected}
          />
        </div>
      </main>

      {/* Footer Compliance Disclaimer */}
      <footer className="border-t border-border bg-card px-6 py-3 flex items-center justify-center">
        <Disclaimer />
      </footer>
    </div>
  );
}
