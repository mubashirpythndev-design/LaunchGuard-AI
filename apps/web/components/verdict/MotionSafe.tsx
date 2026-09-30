"use client";

import React, { ReactNode } from "react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

interface MotionSafeProps {
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Boundary that prevents mounting animated elements/React Bits when reduced motion is preferred.
 *
 * Constitution 4.III: React Bits must NOT be mounted at all rather than mounted with zero duration.
 */
export function MotionSafe({ children, fallback = null }: MotionSafeProps) {
  const prefersReduced = useReducedMotion();

  if (prefersReduced) {
    return fallback ? <>{fallback}</> : null;
  }

  return <>{children}</>;
}
