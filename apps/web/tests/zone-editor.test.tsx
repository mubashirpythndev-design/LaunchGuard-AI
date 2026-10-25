import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import React from "react";
import { ZoneEditor, validateZonePolygon } from "@/components/monitor/ZoneEditor";
import { useMonitorStore } from "@/stores/monitor-store";

describe("ZoneEditor component (T079, T085, FR-012, FR-013)", () => {
  beforeEach(() => {
    act(() => {
      useMonitorStore.getState().reset();
    });
  });

  it("adds normalized points to the Zustand store on click when editing", () => {
    act(() => {
      useMonitorStore.getState().setIsZoneEditing(true);
    });

    render(<ZoneEditor />);

    const svg = screen.getByTestId("zone-editor-svg");

    // Mock getBoundingClientRect
    svg.getBoundingClientRect = () => ({
      left: 0,
      top: 0,
      width: 1000,
      height: 500,
      right: 1000,
      bottom: 500,
      x: 0,
      y: 0,
      toJSON: () => {},
    });

    fireEvent.click(svg, { clientX: 200, clientY: 100 });
    fireEvent.click(svg, { clientX: 800, clientY: 100 });
    fireEvent.click(svg, { clientX: 800, clientY: 400 });

    const points = useMonitorStore.getState().zonePoints;
    expect(points.length).toBe(3);
    expect(points[0]).toEqual([0.2, 0.2]);
    expect(points[1]).toEqual([0.8, 0.2]);
    expect(points[2]).toEqual([0.8, 0.8]);

    // Polygon element should be rendered
    expect(screen.getByTestId("zone-polygon")).toBeInTheDocument();
  });

  it("clears zone points when Clear button is clicked", () => {
    act(() => {
      useMonitorStore.getState().setZonePoints([
        [0.1, 0.1],
        [0.5, 0.1],
        [0.5, 0.5],
      ]);
    });

    render(<ZoneEditor />);

    expect(screen.getByTestId("zone-polygon")).toBeInTheDocument();
    const clearBtn = screen.getByTestId("clear-zone-btn");
    fireEvent.click(clearBtn);

    expect(useMonitorStore.getState().zonePoints).toEqual([]);
    expect(screen.queryByTestId("zone-polygon")).not.toBeInTheDocument();
  });

  it("validates polygon point count (< 3 points)", () => {
    act(() => {
      useMonitorStore.getState().setIsZoneEditing(true);
      useMonitorStore.getState().setZonePoints([
        [0.1, 0.1],
        [0.5, 0.1],
      ]);
    });

    render(<ZoneEditor />);

    const saveBtn = screen.getByTestId("save-zone-btn");
    fireEvent.click(saveBtn);

    const errorAlert = screen.getByTestId("zone-validation-error");
    expect(errorAlert).toBeInTheDocument();
    expect(errorAlert).toHaveTextContent("Danger zone polygon must contain at least 3 points.");
  });

  it("validates polygon self-intersection and zero area", () => {
    // 1. Self-intersecting figure-8
    const selfIntersecting: [number, number][] = [
      [0.1, 0.1],
      [0.9, 0.9],
      [0.9, 0.1],
      [0.1, 0.9],
    ];
    expect(validateZonePolygon(selfIntersecting)).toBe(
      "Danger zone polygon outline is self-intersecting."
    );

    // 2. Collinear / zero-area triangle
    const zeroArea: [number, number][] = [
      [0.1, 0.1],
      [0.5, 0.5],
      [0.9, 0.9],
    ];
    expect(validateZonePolygon(zeroArea)).toBe("Danger zone polygon has zero area.");

    // 3. Valid polygon
    const validPolygon: [number, number][] = [
      [0.2, 0.2],
      [0.8, 0.2],
      [0.8, 0.8],
      [0.2, 0.8],
    ];
    expect(validateZonePolygon(validPolygon)).toBeNull();
  });
});
