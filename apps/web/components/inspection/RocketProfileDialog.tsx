"use client";

import React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Disclaimer } from "@/components/verdict/Disclaimer";

export function RocketProfileDialog({
  open,
  onOpenChange,
  children,
  busy,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
  busy: boolean;
}) {
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!busy) onOpenChange(next);
      }}
    >
      <DialogContent
        className="max-h-[90dvh] w-[calc(100%_-_2rem)] max-w-4xl overflow-y-auto motion-reduce:animate-none"
        onEscapeKeyDown={(event) => {
          if (busy) event.preventDefault();
        }}
        onPointerDownOutside={(event) => {
          if (busy) event.preventDefault();
        }}
      >
        <DialogHeader>
          <DialogTitle>Vehicle profile and golden references</DialogTitle>
          <DialogDescription>
            Register the vehicle and enroll a clear baseline for each quadrant.
          </DialogDescription>
        </DialogHeader>
        {children}
        <Disclaimer />
      </DialogContent>
    </Dialog>
  );
}
