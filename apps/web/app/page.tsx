import Link from "next/link";
import { FileSearch, MonitorPlay, History } from "lucide-react";

export default function HomePage() {
  return (
    <main className="p-6 max-w-7xl mx-auto space-y-6">
      <header className="border-b border-border pb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">LaunchGuard AI</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Operational flight safety console
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-border text-xs font-mono text-muted-foreground bg-card">
            <span className="size-1.5 rounded-full bg-steel"></span>
            System ready
          </span>
        </div>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/inspect"
          className="p-4 rounded-md border border-border bg-card hover:border-steel transition-colors block"
        >
          <div className="flex items-center gap-2 mb-2 text-foreground font-medium text-sm">
            <FileSearch className="size-4 text-steel" />
            Pre-launch inspection
          </div>
          <p className="text-xs text-muted-foreground">
            Upload vehicle imagery to evaluate structural integrity and fin alignment.
          </p>
        </Link>

        <Link
          href="/monitor"
          className="p-4 rounded-md border border-border bg-card hover:border-steel transition-colors block"
        >
          <div className="flex items-center gap-2 mb-2 text-foreground font-medium text-sm">
            <MonitorPlay className="size-4 text-steel" />
            Launchpad monitor
          </div>
          <p className="text-xs text-muted-foreground">
            Real-time optical monitoring of danger exclusion zones and hazardous cues.
          </p>
        </Link>

        <Link
          href="/history"
          className="p-4 rounded-md border border-border bg-card hover:border-steel transition-colors block"
        >
          <div className="flex items-center gap-2 mb-2 text-foreground font-medium text-sm">
            <History className="size-4 text-steel" />
            Inspection history
          </div>
          <p className="text-xs text-muted-foreground">
            Review past evaluation records, telemetry findings, and audit logs.
          </p>
        </Link>
      </section>

      <footer className="text-xs text-muted-foreground border-t border-border pt-4">
        Decision-support tool. Not a replacement for certified range safety.
      </footer>
    </main>
  );
}
