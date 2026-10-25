"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  FileText,
  Filter,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Disclaimer } from "@/components/verdict/Disclaimer";
import { VerdictBadge, type VerdictType } from "@/components/verdict/VerdictBadge";
import type { RunListItem, RunListResponse } from "@launchguard/contract";

const PAGE_SIZE = 10;

export default function HistoryPage() {
  const [selectedVerdict, setSelectedVerdict] = useState<string>("ALL");
  const [page, setPage] = useState<number>(0);
  const [data, setData] = useState<RunListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (selectedVerdict !== "ALL") {
        params.append("verdict", selectedVerdict);
      }
      params.append("limit", PAGE_SIZE.toString());
      params.append("offset", (page * PAGE_SIZE).toString());

      const res = await fetch(`/api/runs?${params.toString()}`);
      if (!res.ok) {
        throw new Error("Failed to load historical runs.");
      }
      const json: RunListResponse = await res.json();
      setData(json);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      setLoading(false);
    }
  }, [selectedVerdict, page]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  const handleFilterChange = (filter: string) => {
    setSelectedVerdict(filter);
    setPage(0);
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="min-h-screen bg-zinc-950 font-sans text-zinc-100 p-4 md:p-8">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Top Operational Navigation */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-4">
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              size="sm"
              asChild
              className="border-zinc-800 text-zinc-300 hover:text-zinc-100"
            >
              <Link href="/">
                <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
                <span>Console Home</span>
              </Link>
            </Button>
            <div>
              <h1 className="text-lg font-bold text-zinc-100">Range Safety Inspection History</h1>
              <p className="text-xs text-zinc-400">
                Audited pre-launch inspections and launchpad danger zone monitor runs
              </p>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchRuns}
            disabled={loading}
            className="border-zinc-800 text-zinc-300 hover:text-zinc-100 font-mono text-xs"
          >
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </Button>
        </div>

        {/* Universal Mandated Disclaimer */}
        <div className="flex justify-between items-center bg-zinc-900/50 border border-zinc-800/80 rounded-md px-3.5 py-2">
          <Disclaimer />
          <span className="text-xs font-mono text-zinc-500">Audit Log</span>
        </div>

        {/* Filter Controls Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-zinc-800 bg-zinc-900/40 p-3">
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-zinc-400" />
            <span className="text-xs font-mono text-zinc-400 uppercase">Filter Verdict:</span>
            <div className="flex items-center space-x-1">
              {["ALL", "GO", "HOLD", "NO-GO"].map((filter) => (
                <button
                  key={filter}
                  type="button"
                  data-testid={`filter-${filter.toLowerCase()}`}
                  onClick={() => handleFilterChange(filter)}
                  className={`rounded px-2.5 py-1 text-xs font-mono font-medium transition-colors ${
                    selectedVerdict === filter
                      ? "bg-zinc-800 text-zinc-100 border border-zinc-700"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
                  }`}
                >
                  {filter}
                </button>
              ))}
            </div>
          </div>

          <div className="text-xs font-mono text-zinc-400">
            {data ? (
              <span>
                Total records: <strong className="text-zinc-200">{data.total}</strong>
              </span>
            ) : null}
          </div>
        </div>

        {/* Historical Runs Table */}
        <div className="rounded-md border border-zinc-800 bg-zinc-900/20 overflow-hidden">
          {loading && !data ? (
            <div className="flex flex-col items-center justify-center p-12 space-y-3">
              <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
              <span className="text-xs font-mono text-zinc-500">Loading audit log...</span>
            </div>
          ) : error ? (
            <div className="p-8 text-center text-xs font-mono text-red-400" role="alert">
              {error}
            </div>
          ) : data?.items.length === 0 ? (
            <div className="p-12 text-center text-xs font-mono text-zinc-500">
              No historical runs found matching the selected filter criteria.
            </div>
          ) : (
            <Table data-testid="history-table">
              <TableHeader>
                <TableRow className="border-zinc-800 hover:bg-transparent">
                  <TableHead className="w-[140px]">Run ID</TableHead>
                  <TableHead className="w-[180px]">Timestamp (UTC)</TableHead>
                  <TableHead className="w-[120px]">Status</TableHead>
                  <TableHead className="w-[100px]">Risk Score</TableHead>
                  <TableHead className="w-[120px]">Verdict</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items.map((item: RunListItem) => (
                  <TableRow
                    key={item.run_id}
                    data-testid={`history-row-${item.run_id}`}
                    className="border-zinc-800/60 hover:bg-zinc-900/50"
                  >
                    <TableCell className="font-mono text-xs font-medium text-zinc-200">
                      {item.run_id.slice(0, 8)}...
                    </TableCell>
                    <TableCell className="font-mono text-xs text-zinc-400">
                      {new Date(item.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center rounded border border-zinc-800 bg-zinc-900 px-2 py-0.5 text-[11px] font-mono uppercase text-zinc-300">
                        {item.status}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-zinc-300">
                      {item.risk_score !== null && item.risk_score !== undefined
                        ? item.risk_score
                        : "—"}
                    </TableCell>
                    <TableCell>
                      {item.verdict ? (
                        <VerdictBadge verdict={item.verdict as VerdictType} size="sm" />
                      ) : (
                        <span className="text-xs font-mono text-zinc-500">Pending</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        asChild
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs font-mono text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800"
                      >
                        <Link href={`/report/${item.run_id}`}>
                          <FileText className="mr-1.5 h-3.5 w-3.5" />
                          <span>View Report</span>
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        {/* Pagination Bar */}
        {data && data.total > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-zinc-800 pt-4">
            <span className="text-xs font-mono text-zinc-400">
              Page {page + 1} of {totalPages}
            </span>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                data-testid="pagination-prev"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0 || loading}
                className="h-8 border-zinc-800 font-mono text-xs"
              >
                <ChevronLeft className="mr-1 h-3.5 w-3.5" />
                <span>Previous</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                data-testid="pagination-next"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1 || loading}
                className="h-8 border-zinc-800 font-mono text-xs"
              >
                <span>Next</span>
                <ChevronRight className="ml-1 h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
