"use client";

import React, { useState, useCallback, useEffect } from "react";
import { z } from "zod";
import { Upload, AlertCircle, FileImage, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { downscaleImageIfNeeded } from "@/lib/upload";

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

const uploadValidationSchema = z.object({
  file: z
    .custom<File>((val) => val instanceof File, "File is required")
    .refine(
      (file) => ACCEPTED_IMAGE_TYPES.includes(file.type),
      "Only JPG, PNG, and WebP images are accepted"
    )
    .refine(
      (file) => file.size <= MAX_FILE_SIZE,
      "File size exceeds 10 MB limit"
    ),
});

export interface UploaderProps {
  onFileSelect?: (file: File, previewUrl: string) => void;
  onError?: (error: string) => void;
  className?: string;
  disabled?: boolean;
}

export function Uploader({
  onFileSelect,
  onError,
  className,
  disabled = false,
}: UploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl && previewUrl.startsWith("blob:")) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const processFile = useCallback(
    async (file: File) => {
      const result = uploadValidationSchema.safeParse({ file });
      if (!result.success) {
        const errorText = result.error.errors[0]?.message ?? "Invalid file selection";
        setErrorMessage(errorText);
        onError?.(errorText);
        return;
      }

      setErrorMessage(null);
      if (previewUrl && previewUrl.startsWith("blob:")) {
        URL.revokeObjectURL(previewUrl);
      }

      const { file: processedFile } = await downscaleImageIfNeeded(file);

      const objectUrl = URL.createObjectURL(processedFile);
      setPreviewUrl(objectUrl);
      setFileName(processedFile.name);
      setFileSize(processedFile.size);
      onFileSelect?.(processedFile, objectUrl);
    },
    [previewUrl, onFileSelect, onError]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (!disabled) {
        setIsDragging(true);
      }
    },
    [disabled]
  );

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;

      const droppedFiles = e.dataTransfer.files;
      if (droppedFiles && droppedFiles.length > 0) {
        processFile(droppedFiles[0]);
      }
    },
    [disabled, processFile]
  );

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFiles = e.target.files;
      if (selectedFiles && selectedFiles.length > 0) {
        processFile(selectedFiles[0]);
      }
      e.target.value = "";
    },
    [processFile]
  );

  const handleClear = useCallback(() => {
    if (previewUrl && previewUrl.startsWith("blob:")) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
    setFileName(null);
    setFileSize(null);
    setErrorMessage(null);
  }, [previewUrl]);

  return (
    <div className={cn("w-full space-y-3", className)}>
      <div
        data-testid="upload-dropzone"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "relative flex flex-col items-center justify-center p-6 border border-dashed rounded-md bg-card transition-colors text-center",
          isDragging ? "border-steel bg-accent/30" : "border-border hover:border-steel/60",
          disabled && "opacity-50 pointer-events-none cursor-not-allowed"
        )}
      >
        <div className="flex flex-col items-center space-y-2">
          <div className="p-2 rounded-md bg-secondary text-muted-foreground">
            <Upload className="w-5 h-5 text-steel" />
          </div>

          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">
              Drag and drop rocket image here
            </p>
            <p className="text-xs text-muted-foreground">
              Supports JPG, PNG, and WebP up to 10 MB
            </p>
          </div>

          <div className="pt-2">
            <label
              htmlFor="file-input"
              className={cn(
                "inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium rounded-md cursor-pointer transition-colors border border-border bg-secondary hover:bg-accent text-secondary-foreground"
              )}
            >
              Select file
            </label>
            <input
              id="file-input"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileInputChange}
              className="sr-only"
              disabled={disabled}
            />
          </div>
        </div>
      </div>

      {errorMessage && (
        <div
          role="alert"
          className="flex items-center gap-2 p-3 text-xs border rounded-md border-destructive/40 bg-destructive/10 text-destructive"
        >
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {previewUrl && (
        <div className="p-3 border rounded-md border-border bg-card space-y-2">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5 truncate">
              <FileImage className="w-4 h-4 text-steel shrink-0" />
              <span className="font-mono truncate">{fileName ?? "Uploaded image"}</span>
              {fileSize !== null && (
                <span className="text-muted-foreground font-mono">
                  ({(fileSize / (1024 * 1024)).toFixed(2)} MB)
                </span>
              )}
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleClear}
              className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
            >
              <X className="w-3.5 h-3.5 mr-1" />
              Remove
            </Button>
          </div>

          <div className="relative overflow-hidden rounded border border-border bg-muted/30 max-h-80 flex items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt="Inspection preview"
              className="object-contain w-full h-auto max-h-80"
            />
          </div>
        </div>
      )}
    </div>
  );
}
