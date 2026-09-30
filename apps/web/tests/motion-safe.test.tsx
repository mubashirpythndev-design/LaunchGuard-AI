import React from "react";
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MotionSafe } from "@/components/verdict/MotionSafe";

describe("MotionSafe boundary (Constitution 4.III, T051)", () => {
  const originalMatchMedia = window.matchMedia;

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
    vi.restoreAllMocks();
  });

  it("renders animated child when reduced motion is NOT preferred", () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    render(
      <MotionSafe>
        <div data-testid="react-bits-child">Animated Content</div>
      </MotionSafe>,
    );

    expect(screen.queryByTestId("react-bits-child")).not.toBeNull();
    expect(screen.getByTestId("react-bits-child").textContent).toBe("Animated Content");
  });

  it("does NOT mount React Bits child when reduced motion IS preferred", () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    render(
      <MotionSafe fallback={<div data-testid="static-fallback">Static Fallback</div>}>
        <div data-testid="react-bits-child">Animated Content</div>
      </MotionSafe>,
    );

    // React Bits child must NOT be mounted at all
    expect(screen.queryByTestId("react-bits-child")).toBeNull();
    // Fallback is mounted instead
    expect(screen.queryByTestId("static-fallback")).not.toBeNull();
  });
});
