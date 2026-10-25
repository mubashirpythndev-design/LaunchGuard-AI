import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MultiAngleUploader } from "@/components/inspection/MultiAngleUploader";
import { QuadrantResults } from "@/components/inspection/QuadrantResults";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Day 4 field capture", () => {
  it("reports denied camera access and retains upload fallback", async () => {
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockRejectedValue(new Error("Camera permission denied")) },
    });
    render(
      <MultiAngleUploader disabled={false} onCapture={vi.fn()}>
        <p>Upload fallback</p>
      </MultiAngleUploader>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Start camera" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Camera permission denied");
    expect(screen.getByText("Upload fallback")).toBeVisible();
  });

  it("releases a stream that arrives after the capture station unmounts", async () => {
    let finish: ((value: MediaStream) => void) | undefined;
    const pending = new Promise<MediaStream>((resolve) => {
      finish = resolve;
    });
    const stop = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockReturnValue(pending) },
    });
    const view = render(
      <MultiAngleUploader disabled={false} onCapture={vi.fn()}>
        <p>Upload fallback</p>
      </MultiAngleUploader>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Start camera" }));
    view.unmount();
    finish?.({ getTracks: () => [{ stop }] } as unknown as MediaStream);
    await waitFor(() => expect(stop).toHaveBeenCalledOnce());
  });

  it("renders actual cv.reference findings as switchable comparison contours", () => {
    render(
      <QuadrantResults
        images={[
          {
            quadrant: "front",
            image_url: "/raw.jpg",
            reference_image_url: "/reference.jpg",
            aligned_image_url: "/aligned.jpg",
          },
        ]}
        findings={[
          {
            quadrant: "front",
            module: "cv.reference",
            check_id: "reference.structural_deviation",
            severity: "critical",
            message: "Possible deviation",
            confidence: 0.9,
            metrics: [{ name: "deviation_area_pct", value: 3, unit: "%" }],
            overlay: {
              kind: "polygon",
              check_id: "reference.structural_deviation",
              points: [
                [0.1, 0.2],
                [0.6, 0.2],
                [0.4, 0.7],
              ],
            },
          },
        ]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Show difference contours" }));
    expect(
      screen.getByLabelText("Reference difference contours").querySelector("polygon"),
    ).toHaveAttribute("points", "100,200 600,200 400,700");
    fireEvent.click(screen.getByRole("button", { name: "Hide difference contours" }));
    expect(screen.queryByLabelText("Reference difference contours")).not.toBeInTheDocument();
  });
});
