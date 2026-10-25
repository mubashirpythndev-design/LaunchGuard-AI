import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import React from "react";
import { AnnotatedViewer } from "@/components/inspection/AnnotatedViewer";
import type { FindingSchema } from "@/lib/schemas";

const mockFindings: FindingSchema[] = [
  {
    module: "cv.body",
    check_id: "body.cracks",
    severity: "warning",
    message: "Possible surface crack detected",
    confidence: 0.85,
    metrics: [{ name: "crack_length", value: 12.4, unit: "mm" }],
    overlay: {
      kind: "bbox",
      check_id: "body.cracks",
      points: [
        [0.2, 0.3],
        [0.4, 0.5],
      ],
      label: "Crack A",
    },
    step_position: 1,
    degraded: false,
    low_confidence_critical: false,
  },
  {
    module: "cv.fins",
    check_id: "fin.alignment",
    severity: "critical",
    message: "Fin angle deviation 7.2 deg",
    confidence: 0.92,
    metrics: [{ name: "fin_angle_deviation", value: 7.2, unit: "deg", error_margin: 1.5, threshold: 6.0 }],
    overlay: {
      kind: "arc",
      check_id: "fin.alignment",
      points: [[0.5, 0.8]],
      radius: 0.1,
      start_deg: 0,
      end_deg: 7.2,
      label: "Fin 1 Deviation",
    },
    step_position: 2,
    degraded: false,
    low_confidence_critical: false,
  },
];

describe("AnnotatedViewer component (T057, FR-010, FR-013)", () => {
  it("renders base image and SVG overlay layer", () => {
    render(<AnnotatedViewer imageUrl="/demo/normal.jpg" findings={mockFindings} />);
    expect(screen.getByAltText(/annotated rocket view/i)).toBeInTheDocument();
    expect(screen.getByTestId("overlay-svg")).toBeInTheDocument();
  });

  it("renders overlay elements based on normalized coordinates", () => {
    render(<AnnotatedViewer imageUrl="/demo/normal.jpg" findings={mockFindings} />);
    // Bbox overlay for body.cracks
    expect(screen.getByTestId("overlay-bbox-body.cracks")).toBeInTheDocument();
    // Arc overlay for fin.alignment
    expect(screen.getByTestId("overlay-arc-fin.alignment")).toBeInTheDocument();
  });

  it("toggles module overlays on and off", () => {
    render(<AnnotatedViewer imageUrl="/demo/normal.jpg" findings={mockFindings} showControls={true} />);

    // Initially both visible
    expect(screen.getByTestId("overlay-bbox-body.cracks")).toBeInTheDocument();
    expect(screen.getByTestId("overlay-arc-fin.alignment")).toBeInTheDocument();

    // Toggle body off
    const bodyToggle = screen.getByLabelText(/toggle body overlays/i);
    fireEvent.click(bodyToggle);

    expect(screen.queryByTestId("overlay-bbox-body.cracks")).not.toBeInTheDocument();
    expect(screen.getByTestId("overlay-arc-fin.alignment")).toBeInTheDocument();
  });
});
