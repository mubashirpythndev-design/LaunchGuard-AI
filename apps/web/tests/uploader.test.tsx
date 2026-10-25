import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { Uploader } from "@/components/inspection/Uploader";

describe("Uploader component (T056, FR-007, FR-008)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.URL.createObjectURL = vi.fn(() => "blob:http://localhost/mock-preview");
    global.URL.revokeObjectURL = vi.fn();
  });

  it("renders drag-drop area and file input", () => {
    render(<Uploader onFileSelect={vi.fn()} />);
    expect(screen.getByText(/drag and drop rocket image/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/select file/i)).toBeInTheDocument();
  });

  it("accepts valid image via file input and renders preview immediately", async () => {
    const onSelect = vi.fn();
    render(<Uploader onFileSelect={onSelect} />);

    const file = new File(["dummy-image-content"], "rocket.jpg", { type: "image/jpeg" });
    const input = screen.getByLabelText(/select file/i) as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByAltText(/inspection preview/i)).toBeInTheDocument();
      expect(onSelect).toHaveBeenCalledWith(file, "blob:http://localhost/mock-preview");
    });
  });

  it("validates file type and rejects non-image files inline", async () => {
    const onSelect = vi.fn();
    render(<Uploader onFileSelect={onSelect} />);

    const invalidFile = new File(["pdf data"], "document.pdf", { type: "application/pdf" });
    const input = screen.getByLabelText(/select file/i) as HTMLInputElement;

    fireEvent.change(input, { target: { files: [invalidFile] } });

    await waitFor(() => {
      expect(screen.getByText(/only jpg, png, and webp images are accepted/i)).toBeInTheDocument();
      expect(onSelect).not.toHaveBeenCalled();
    });
  });

  it("validates file size and rejects files exceeding 10 MB", async () => {
    const onSelect = vi.fn();
    render(<Uploader onFileSelect={onSelect} />);

    // Mock 11 MB file
    const largeFile = new File([new ArrayBuffer(11 * 1024 * 1024)], "huge.png", { type: "image/png" });
    const input = screen.getByLabelText(/select file/i) as HTMLInputElement;

    fireEvent.change(input, { target: { files: [largeFile] } });

    await waitFor(() => {
      expect(screen.getByText(/file size exceeds 10 mb limit/i)).toBeInTheDocument();
      expect(onSelect).not.toHaveBeenCalled();
    });
  });

  it("handles drag and drop correctly", async () => {
    const onSelect = vi.fn();
    render(<Uploader onFileSelect={onSelect} />);

    const file = new File(["dummy-image-content"], "dragged.jpg", { type: "image/jpeg" });
    const dropZone = screen.getByTestId("upload-dropzone");

    fireEvent.drop(dropZone, {
      dataTransfer: {
        files: [file],
      },
    });

    await waitFor(() => {
      expect(screen.getByAltText(/inspection preview/i)).toBeInTheDocument();
      expect(onSelect).toHaveBeenCalledWith(file, "blob:http://localhost/mock-preview");
    });
  });
});
