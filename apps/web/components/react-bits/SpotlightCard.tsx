"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";

interface SpotlightCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function SpotlightCard({
  children,
  className = "",
  ...props
}: SpotlightCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={cn(
        "relative rounded-md border border-border bg-card p-4 transition-colors",
        isHovered ? "border-steel/50 bg-card" : "border-border bg-card",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
