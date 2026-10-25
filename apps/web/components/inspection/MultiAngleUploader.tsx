"use client";

import React, { useEffect, useRef, useState } from "react";
import { Camera, CameraOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { QuadrantImageSchema } from "@/lib/schemas";
import { ANGLES } from "./QuadrantResults";
import { CameraGuideHUD } from "./CameraGuideHUD";

export function MultiAngleUploader({
  children,
  disabled,
  onCapture,
}: {
  children: React.ReactNode;
  disabled: boolean;
  onCapture: (quadrant: QuadrantImageSchema["quadrant"], file: File) => void;
}) {
  const [angle, setAngle] = useState<QuadrantImageSchema["quadrant"]>("front");
  const [streaming, setStreaming] = useState(false);
  const [guide, setGuide] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [starting, setStarting] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const generation = useRef(0);
  function stop() {
    generation.current += 1;
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    if (video.current) video.current.srcObject = null;
    setStreaming(false);
    setStarting(false);
    setReady(false);
  }
  useEffect(
    () => () => {
      generation.current += 1;
      stream.current?.getTracks().forEach((track) => track.stop());
    },
    [],
  );
  async function start() {
    if (starting || streaming) return;
    setStarting(true);
    const request = ++generation.current;
    setError(null);
    try {
      if (!navigator.mediaDevices?.getUserMedia)
        throw new Error("Camera capture requires localhost or HTTPS. You can still upload images.");
      const next = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 960 }, facingMode: "environment" },
        audio: false,
      });
      if (request !== generation.current) {
        next.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = next;
      next.getVideoTracks().forEach((track) => {
        track.onended = () => {
          stop();
          setError("Camera disconnected. Reconnect or upload an image.");
        };
      });
      if (video.current) {
        video.current.srcObject = next;
        await video.current.play();
      }
      if (request !== generation.current) return;
      setStreaming(true);
      setStarting(false);
    } catch (cause: unknown) {
      if (request !== generation.current) return;
      stop();
      setError(
        cause instanceof Error ? cause.message : "Camera access failed. Upload an image instead.",
      );
    }
  }
  function capture() {
    const source = video.current;
    if (!source || !ready || disabled || capturing) return;
    setCapturing(true);
    const target = angle;
    const canvas = document.createElement("canvas");
    canvas.width = source.videoWidth;
    canvas.height = source.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      setError("Image capture unavailable. Upload an image instead.");
      setCapturing(false);
      return;
    }
    context.drawImage(source, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (blob)
          onCapture(target, new File([blob], `${target}-capture.jpg`, { type: "image/jpeg" }));
        else setError("Could not capture an image. Try again.");
        setCapturing(false);
      },
      "image/jpeg",
      0.92,
    );
  }
  return (
    <section className="space-y-4" aria-label="Four-quadrant capture station">
      <div className="rounded-md border border-border bg-card p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-mono uppercase tracking-widest text-steel">
              Field capture station
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Choose the camera angle, match the baseline framing, and capture.
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            disabled={disabled || starting}
            onClick={() => (streaming ? stop() : void start())}
          >
            {streaming ? <CameraOff /> : <Camera />}
            {starting ? "Connecting camera..." : streaming ? "Stop camera" : "Start camera"}
          </Button>
        </div>
        <Tabs
          value={angle}
          onValueChange={(value) => {
            const match = ANGLES.find((item) => item.key === value);
            if (match) setAngle(match.key);
          }}
        >
          <TabsList className="grid w-full grid-cols-4 h-auto">
            {ANGLES.map((item) => (
              <TabsTrigger disabled={disabled} key={item.key} value={item.key}>
                {item.degrees}&deg; {item.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <div hidden={!streaming} className="space-y-3">
          <div className="relative mx-auto aspect-[4/3] max-w-xl overflow-hidden rounded-md border border-border bg-background">
            <video
              ref={video}
              muted
              playsInline
              className="h-full w-full object-contain"
              onLoadedData={() => setReady(true)}
              aria-label="Live quadrant camera"
            />
            {guide && <CameraGuideHUD label={angle} />}
          </div>
          <div className="flex flex-wrap justify-between gap-3">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={guide}
                onChange={(event) => setGuide(event.target.checked)}
              />
              Alignment guide
            </label>
            <Button type="button" disabled={disabled || !ready || capturing} onClick={capture}>
              Capture {angle} image
            </Button>
          </div>
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </div>
      {children}
    </section>
  );
}
