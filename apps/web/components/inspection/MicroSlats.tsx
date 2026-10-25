"use client";

import React from "react";
import { motion, useReducedMotion } from "motion/react";

export function MicroSlats({ count }: { count: number }) {
  const reducedMotion = useReducedMotion();
  return (
    <div className="mt-3 flex gap-1" aria-hidden="true">
      {[0, 1, 2, 3].map((index) => (
        <motion.span
          key={index}
          className="h-1.5 w-8 bg-steel"
          animate={{ opacity: index < count ? 1 : 0.2 }}
          transition={{ duration: reducedMotion ? 0 : 0.2 }}
        />
      ))}
    </div>
  );
}
