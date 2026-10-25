"use client";

import React, { useEffect, useRef } from "react";
import { useInView, useMotionValue, useSpring, useReducedMotion } from "motion/react";

interface CountUpProps {
  to: number;
  from?: number;
  direction?: "up" | "down";
  delay?: number;
  duration?: number;
  className?: string;
  startWhen?: boolean;
  separator?: string;
}

export function CountUp({
  to,
  from = 0,
  direction = "up",
  delay = 0,
  duration = 1.5,
  className = "",
  startWhen = true,
  separator = "",
}: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const reducedMotion = useReducedMotion();
  const motionValue = useMotionValue(direction === "down" ? to : from);

  const damping = 20 + 40 * (1 / duration);
  const stiffness = 100 * (1 / duration);

  const springValue = useSpring(motionValue, {
    damping,
    stiffness,
  });

  const isInView = useInView(ref, { once: true, margin: "0px" });

  useEffect(() => {
    if (ref.current) {
      ref.current.textContent = String(reducedMotion ? to : direction === "down" ? to : from);
    }
  }, [from, to, direction, reducedMotion]);

  useEffect(() => {
    if (!reducedMotion && isInView && startWhen) {
      const timer = setTimeout(() => {
        motionValue.set(direction === "down" ? from : to);
      }, delay * 1000);

      return () => clearTimeout(timer);
    }
  }, [isInView, startWhen, motionValue, direction, from, to, delay, reducedMotion]);

  useEffect(() => {
    const unsubscribe = springValue.on("change", (latest: number) => {
      if (ref.current && !reducedMotion) {
        const formatted = Math.round(latest).toLocaleString();
        ref.current.textContent = separator ? formatted.replace(/,/g, separator) : formatted;
      }
    });

    return () => unsubscribe();
  }, [springValue, separator, reducedMotion]);

  return (
    <span className={`num ${className}`} ref={ref}>
      {to}
    </span>
  );
}
