/**
 * SSE-safe streaming reverse proxy for backend API communication (Constitution 3.I, Research R5).
 */
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_BASE = process.env.API_URL || "http://127.0.0.1:8000";

async function proxyRequest(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const targetPath = `/api/${path.join("/")}`;
  const targetUrl = new URL(targetPath, API_BASE);
  targetUrl.search = req.nextUrl.search;

  const headers = new Headers(req.headers);
  headers.delete("host");

  const body =
    req.method !== "GET" && req.method !== "HEAD" ? await req.blob() : undefined;

  try {
    const upstreamRes = await fetch(targetUrl.toString(), {
      method: req.method,
      headers,
      body,
      signal: req.signal,
      // @ts-expect-error duplex option is valid in node fetch for streaming bodies
      duplex: "half",
    });

    const isSSE =
      upstreamRes.headers.get("content-type")?.includes("text/event-stream") ?? false;

    const resHeaders = new Headers(upstreamRes.headers);
    // Strip content-length to guarantee chunked streaming
    resHeaders.delete("content-length");

    if (isSSE) {
      resHeaders.set("Content-Type", "text/event-stream; charset=utf-8");
      resHeaders.set("Cache-Control", "no-cache, no-transform");
      resHeaders.set("Connection", "keep-alive");
      resHeaders.set("X-Accel-Buffering", "no");
    }

    return new NextResponse(upstreamRes.body, {
      status: upstreamRes.status,
      statusText: upstreamRes.statusText,
      headers: resHeaders,
    });
  } catch (err: unknown) {
    if ((err as Error)?.name === "AbortError") {
      return new NextResponse(null, { status: 499 });
    }
    console.error("[Proxy Error]:", err);
    return NextResponse.json(
      {
        error: {
          code: "PROXY_ERROR",
          message: "Failed to communicate with upstream API service.",
          field: null,
        },
      },
      { status: 502 },
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
