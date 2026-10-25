"use client";

import React from "react";
import { useReducedMotion } from "motion/react";
import DecryptedText from "@/components/react-bits/DecryptedText";

export function TelemetryHeading() {
  const reducedMotion = useReducedMotion();
  const text = "Vehicle inspection / four-angle capture";
  return reducedMotion ? (
    <span>{text}</span>
  ) : (
    <DecryptedText
      text={text}
      animateOn="hover"
      speed={35}
      maxIterations={6}
      characters="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    />
  );
}
