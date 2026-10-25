"use client";

import React from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useMonitorStore, type MonitorSource } from "@/stores/monitor-store";
import { Camera, Video, Image as ImageIcon } from "lucide-react";

interface SourceSelectorProps {
  onImageSelected?: (file: File) => void;
  onVideoSelected?: (file: File) => void;
  className?: string;
}

export function SourceSelector({
  onImageSelected,
  onVideoSelected,
  className = "",
}: SourceSelectorProps) {
  const { source, setSource, isMonitoring } = useMonitorStore();

  const handleTabChange = (val: string) => {
    setSource(val as MonitorSource);
  };

  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    type: "image" | "video"
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (type === "image" && onImageSelected) {
      onImageSelected(file);
    } else if (type === "video" && onVideoSelected) {
      onVideoSelected(file);
    }
  };

  return (
    <div
      data-testid="source-selector"
      className={`flex flex-col gap-2 p-3 rounded-md border border-border bg-card ${className}`}
    >
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-foreground tracking-wide uppercase">
          Feed Input Source
        </label>
        {isMonitoring && (
          <span className="flex items-center gap-1.5 text-xs font-mono text-go">
            <span className="w-2 h-2 rounded-full bg-go animate-pulse" />
            STREAMING
          </span>
        )}
      </div>

      <Tabs value={source} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-3 bg-secondary/50">
          <TabsTrigger
            value="webcam"
            data-testid="source-tab-webcam"
            className="flex items-center gap-2"
          >
            <Camera className="w-3.5 h-3.5" />
            <span>Live Camera</span>
          </TabsTrigger>

          <TabsTrigger
            value="video"
            data-testid="source-tab-video"
            className="flex items-center gap-2"
          >
            <Video className="w-3.5 h-3.5" />
            <span>Video Stream</span>
          </TabsTrigger>

          <TabsTrigger
            value="image"
            data-testid="source-tab-image"
            className="flex items-center gap-2"
          >
            <ImageIcon className="w-3.5 h-3.5" />
            <span>Test Frame</span>
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* File pickers for offline/replay sources */}
      {source === "image" && (
        <div className="mt-1">
          <label className="block text-xs text-muted-foreground mb-1">
            Select high-resolution frame (JPEG / PNG):
          </label>
          <input
            type="file"
            accept="image/jpeg,image/png"
            data-testid="image-input"
            onChange={(e) => handleFileChange(e, "image")}
            className="block w-full text-xs text-foreground file:mr-2 file:py-1 file:px-2.5 file:rounded-md file:border file:border-border file:text-xs file:bg-secondary file:text-secondary-foreground hover:file:bg-muted cursor-pointer"
          />
        </div>
      )}

      {source === "video" && (
        <div className="mt-1">
          <label className="block text-xs text-muted-foreground mb-1">
            Select recorded launchpad feed (MP4 / WebM):
          </label>
          <input
            type="file"
            accept="video/mp4,video/webm"
            data-testid="video-input"
            onChange={(e) => handleFileChange(e, "video")}
            className="block w-full text-xs text-foreground file:mr-2 file:py-1 file:px-2.5 file:rounded-md file:border file:border-border file:text-xs file:bg-secondary file:text-secondary-foreground hover:file:bg-muted cursor-pointer"
          />
        </div>
      )}
    </div>
  );
}
