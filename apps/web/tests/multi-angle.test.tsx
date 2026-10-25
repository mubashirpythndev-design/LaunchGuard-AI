import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MultiAngleInspection } from "@/components/inspection/MultiAngleInspection";
import { QuadrantResults } from "@/components/inspection/QuadrantResults";
import { ComparisonSlider } from "@/components/inspection/ComparisonSlider";
import type { FindingSchema } from "@/lib/schemas";

vi.mock("@/hooks/use-run-stream", () => ({
  useRunStream: () => ({ status: "idle", findings: [], verdict: null }),
}));

const angles = ["Front", "Right", "Back", "Left"];

function renderWorkspace() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MultiAngleInspection />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            total: 1,
            items: [
              {
                id: "rocket-1",
                name: "Aero-X",
                vehicle_class: "Research",
                created_at: "2026-10-08",
              },
            ],
          }),
          { headers: { "Content-Type": "application/json" } },
        ),
    ),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function selectRocket() {
  await screen.findByRole("option", { name: "Aero-X / Research" });
  fireEvent.change(screen.getByLabelText("01 / Vehicle profile"), {
    target: { value: "rocket-1" },
  });
}

function upload(label: string, type = "image/jpeg") {
  fireEvent.change(screen.getByLabelText(`${label} image`), {
    target: { files: [new File(["image"], `${label}.jpg`, { type })] },
  });
}

describe("four-angle capture workspace", () => {
  it("requires a vehicle and four captures, and removal revokes coverage", async () => {
    renderWorkspace();
    const submit = screen.getByRole("button", { name: "Run four-angle inspection" });
    expect(submit).toBeDisabled();
    await selectRocket();
    for (const angle of angles.slice(0, 3)) upload(angle);
    expect(submit).toBeDisabled();
    upload("Left");
    await waitFor(() => expect(submit).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Remove Back image" }));
    await waitFor(() => expect(submit).toBeDisabled());
    expect(URL.revokeObjectURL).toHaveBeenCalled();
  });

  it("blocks invalid images and preserves the four multipart field mappings", async () => {
    renderWorkspace();
    await selectRocket();
    for (const angle of angles) upload(angle);
    upload("Back", "application/pdf");
    expect(await screen.findByText("Use JPG, PNG, or WebP")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Run four-angle inspection" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    upload("Back");
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            code: "TEST",
            message: "Test server rejected inspection",
          },
        }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Run four-angle inspection" }));
    expect(await screen.findByText("Test server rejected inspection")).toBeInTheDocument();
    const request = vi.mocked(fetch).mock.calls.find(([url]) => url === "/api/inspections");
    const body = request?.[1]?.body;
    expect(body).toBeInstanceOf(FormData);
    if (!(body instanceof FormData)) throw new Error("Missing multipart body");
    expect(body.get("rocket_id")).toBe("rocket-1");
    for (const angle of angles)
      expect((body.get(angle.toLowerCase()) as File).name).toBe(`${angle}.jpg`);
    expect(body.has("file")).toBe(false);
  });

  it("registers a vehicle with all four golden references", async () => {
    const rocket = {
      id: "rocket-2",
      name: "Aero-R",
      vehicle_class: "Research",
      created_at: "2026-10-08",
      references: [],
      reference_count: 4,
    };
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? "GET";
      if (path === "/api/rockets" && method === "POST") {
        return new Response(JSON.stringify(rocket), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (path.includes("/references/") && method === "POST") {
        return new Response(
          JSON.stringify({
            id: "reference-id",
            rocket_id: rocket.id,
            quadrant: path.split("/").at(-1),
            image_url: path,
            keypoint_count: 80,
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(JSON.stringify({ total: 1, items: [rocket] }), {
        headers: { "Content-Type": "application/json" },
      });
    });

    renderWorkspace();
    fireEvent.click(screen.getByRole("button", { name: "Register vehicle" }));
    fireEvent.change(screen.getByLabelText("Vehicle name"), {
      target: { value: rocket.name },
    });
    fireEvent.change(screen.getByLabelText("Vehicle class"), {
      target: { value: rocket.vehicle_class },
    });
    for (const angle of angles) {
      fireEvent.change(screen.getByLabelText(`${angle} golden reference`), {
        target: {
          files: [new File(["baseline"], `${angle}.jpg`, { type: "image/jpeg" })],
        },
      });
    }
    fireEvent.click(screen.getByRole("button", { name: "Save vehicle and references" }));

    await waitFor(() => {
      for (const angle of angles) {
        expect(fetch).toHaveBeenCalledWith(
          `/api/rockets/${rocket.id}/references/${angle.toLowerCase()}`,
          expect.objectContaining({ method: "POST" }),
        );
      }
      expect(screen.getByLabelText("01 / Vehicle profile")).toHaveValue(rocket.id);
    });
  });

  it("isolates evidence and overlays by quadrant while retaining repeated check IDs", () => {
    const findings: FindingSchema[] = angles.map((angle) => ({
      module: "cv.body",
      check_id: "body.cracks",
      severity: "warning",
      confidence: 0.8,
      message: `${angle} evidence`,
      quadrant: angle.toLowerCase() as FindingSchema["quadrant"],
      metrics: [{ name: "count", value: 1, unit: "count" }],
    }));
    render(<QuadrantResults images={[]} findings={findings} />);
    expect(screen.getByText("Front evidence")).toBeInTheDocument();
    expect(screen.queryByText("Back evidence")).not.toBeInTheDocument();
    fireEvent.mouseDown(screen.getByRole("tab", { name: /Back 180/ }), {
      button: 0,
      ctrlKey: false,
    });
    expect(screen.getByText("Back evidence")).toBeInTheDocument();
    expect(screen.queryByText("Front evidence")).not.toBeInTheDocument();
    expect(screen.getByText(/Coverage is incomplete/)).toBeInTheDocument();
  });
});

describe("golden reference evidence", () => {
  it("supports slider, contour, and difference-map inspection modes", () => {
    const finding: FindingSchema = {
      module: "cv.reference",
      check_id: "reference.structural_deviation",
      severity: "critical",
      confidence: 0.92,
      message: "Surface appears to show a possible structural deviation.",
      quadrant: "front",
      metrics: [{ name: "deviation_area_pct", value: 2.4, unit: "%" }],
      overlay: {
        kind: "polygon",
        check_id: "reference.structural_deviation",
        points: [
          [0.2, 0.2],
          [0.5, 0.2],
          [0.4, 0.6],
        ],
      },
    };
    render(
      <ComparisonSlider
        baselineUrl="/baseline.jpg"
        currentUrl="/current.jpg"
        heatmapUrl="/heatmap.jpg"
        findings={[finding]}
      />,
    );

    const range = screen.getByRole("slider", { name: "Comparison reveal position" });
    fireEvent.change(range, { target: { value: "72" } });
    expect(screen.getByAltText("Aligned current capture")).toHaveStyle({
      clipPath: "inset(0 0 0 72%)",
    });

    fireEvent.click(screen.getByRole("button", { name: "Contours" }));
    expect(
      screen.getByTestId("overlay-polygon-reference.structural_deviation"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Difference map" }));
    expect(screen.getByAltText("Reference comparison difference map")).toHaveAttribute(
      "src",
      "/heatmap.jpg",
    );
  });
});
