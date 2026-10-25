"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { AlertOctagon, ArrowLeft, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Disclaimer } from "@/components/verdict/Disclaimer";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorBoundary({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error("[LaunchGuard Error Boundary]", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-zinc-950 font-sans text-zinc-100 flex flex-col justify-between p-6 md:p-12">
      <div className="mx-auto max-w-xl w-full my-auto space-y-6 text-center">
        <div className="mx-auto h-12 w-12 rounded-full border border-red-900/60 bg-red-950/40 flex items-center justify-center text-red-400">
          <AlertOctagon className="h-6 w-6" />
        </div>

        <div className="space-y-2">
          <span className="text-xs font-mono uppercase tracking-wider text-red-400">
            System Fault Intercepted
          </span>
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-zinc-100">
            Operational Console Exception
          </h1>
          <p className="text-xs text-zinc-400 leading-relaxed font-mono">
            {error.message || "An unhandled exception occurred during safety evaluation."}
          </p>
          {error.digest && (
            <p className="text-[11px] font-mono text-zinc-500">
              Digest: {error.digest}
            </p>
          )}
        </div>

        <div className="flex items-center justify-center gap-3 pt-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => reset()}
            className="border-zinc-800 bg-zinc-900 text-zinc-300 hover:text-zinc-100 font-mono text-xs"
          >
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
            <span>Retry Operation</span>
          </Button>

          <Button
            asChild
            size="sm"
            className="bg-blue-600 hover:bg-blue-500 font-mono text-xs uppercase"
          >
            <Link href="/">
              <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
              <span>Console Home</span>
            </Link>
          </Button>
        </div>
      </div>

      <footer className="mx-auto max-w-xl w-full border-t border-zinc-900 pt-4 flex justify-center">
        <Disclaimer />
      </footer>
    </div>
  );
}
