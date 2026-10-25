"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useMonitorStore, type ZoneStatus } from "@/stores/monitor-store";
import type { FrameAnalysisResponse } from "@launchguard/contract";

interface UseWebcamOptions {
  frameRate?: number; // Target capture rate in fps, default 5
}

export function useWebcam(options: UseWebcamOptions = {}) {
  const { frameRate = 5 } = options;
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const inFlightRef = useRef<boolean>(false);
  const timerRef = useRef<number | null>(null);

  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [cameraError, setCameraError] = useState<string | null>(null);

  const {
    runId,
    isMonitoring,
    zonePoints,
    setLiveStatus,
    setProcessingMs,
    setFps,
    setFindings,
    addLogEntry,
    setIsStale,
    setValidationError,
  } = useMonitorStore();

  const stopStream = useCallback(() => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      for (const track of streamRef.current.getTracks()) {
        track.stop();
      }
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsStreaming(false);
    setIsStale(true);
    inFlightRef.current = false;
  }, [setIsStale]);

  const startStream = useCallback(async () => {
    try {
      setCameraError(null);
      setIsStale(false);

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "environment",
        },
        audio: false,
      });

      streamRef.current = stream;

      // Handle unexpected track end / disconnect
      stream.getVideoTracks().forEach((track) => {
        track.onended = () => {
          stopStream();
          setIsStale(true);
        };
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }

      setIsStreaming(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unable to access camera feed";
      setCameraError(msg);
      setIsStreaming(false);
      setIsStale(true);
    }
  }, [stopStream, setIsStale]);

  // Frame capture and transmission loop (single frame in flight)
  useEffect(() => {
    if (!isStreaming || !isMonitoring || !runId) {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    const intervalMs = Math.round(1000 / frameRate);
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    let lastFrameTime = performance.now();

    const captureTick = async () => {
      // Enforce single-frame-in-flight: skip capture if previous request is still pending
      if (inFlightRef.current) {
        return;
      }

      const video = videoRef.current;
      if (!video || video.readyState < 2 || !ctx) {
        return;
      }

      const width = video.videoWidth || 640;
      const height = video.videoHeight || 360;

      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }

      ctx.drawImage(video, 0, 0, width, height);

      canvas.toBlob(
        async (blob) => {
          if (!blob) return;

          inFlightRef.current = true;
          const requestStart = performance.now();

          try {
            const res = await fetch(`/api/monitor/${runId}/frame`, {
              method: "POST",
              headers: {
                "Content-Type": "image/jpeg",
              },
              body: blob,
            });

            if (res.status === 409) {
              setValidationError("No danger zone defined. Draw and save a zone to monitor clearance.");
              return;
            }

            if (!res.ok) {
              setIsStale(true);
              return;
            }

            const data: FrameAnalysisResponse = await res.json();
            const now = performance.now();
            const elapsed = now - requestStart;
            const currentFps = 1000 / (now - lastFrameTime);
            lastFrameTime = now;

            setProcessingMs(Math.round(data.processing_ms || elapsed));
            setFps(Math.round(currentFps * 10) / 10);
            setLiveStatus(data.zone_status as ZoneStatus);
            setFindings(data.findings || []);
            setIsStale(false);

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
          } catch {
            setIsStale(true);
          } finally {
            inFlightRef.current = false;
          }
        },
        "image/jpeg",
        0.85
      );
    };

    timerRef.current = window.setInterval(captureTick, intervalMs);

    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [
    isStreaming,
    isMonitoring,
    runId,
    frameRate,
    zonePoints,
    setLiveStatus,
    setProcessingMs,
    setFps,
    setFindings,
    addLogEntry,
    setIsStale,
    setValidationError,
  ]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopStream();
    };
  }, [stopStream]);

  return {
    videoRef,
    isStreaming,
    cameraError,
    startStream,
    stopStream,
  };
}
