"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface AnimatedListProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function AnimatedList({
  children,
  className = "",
  ...props
}: AnimatedListProps) {
  return (
    <div className={cn("flex flex-col space-y-2", className)} {...props}>
      {children}
    </div>
  );
}
