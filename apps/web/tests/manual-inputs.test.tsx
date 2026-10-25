import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ManualInputsDialog } from "@/components/report/ManualInputsDialog";

describe("ManualInputsDialog (T104, FR-023)", () => {
  it("renders form fields when open", () => {
    render(
      <ManualInputsDialog
        open={true}
        runId="test-run-dialog"
        onSubmit={vi.fn()}
      />
    );

    expect(screen.getByText(/Manual Verification Required/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Surface Wind Speed/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Atmospheric Visibility/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Precipitation/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Pad exclusion zone cleared/i)).toBeInTheDocument();
  });

  it("rejects negative wind speed inline and does not submit", async () => {
    const onSubmit = vi.fn();
    render(
      <ManualInputsDialog
        open={true}
        runId="test-run-dialog"
        onSubmit={onSubmit}
      />
    );

    const windInput = screen.getByLabelText(/Surface Wind Speed/i);
    const areaCleared = screen.getByLabelText(/Pad exclusion zone cleared/i);
    const submitBtn = screen.getByRole("button", { name: /Resume Inspection/i });

    // Enter negative wind speed
    fireEvent.change(windInput, { target: { value: "-5.0" } });
    fireEvent.click(areaCleared);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByTestId("error-wind-speed")).toBeInTheDocument();
      expect(screen.getByText(/Wind speed cannot be negative/i)).toBeInTheDocument();
    });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits valid inputs to the onSubmit handler", async () => {
    const onSubmit = vi.fn();
    render(
      <ManualInputsDialog
        open={true}
        runId="test-run-dialog"
        onSubmit={onSubmit}
      />
    );

    const windInput = screen.getByLabelText(/Surface Wind Speed/i);
    const areaCleared = screen.getByLabelText(/Pad exclusion zone cleared/i);
    const submitBtn = screen.getByRole("button", { name: /Resume Inspection/i });

    fireEvent.change(windInput, { target: { value: "8.5" } });
    fireEvent.click(areaCleared);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        wind_speed_ms: 8.5,
        visibility: "good",
        precipitation: "none",
        area_cleared: true,
        notes: "",
      });
    });
  });
});
