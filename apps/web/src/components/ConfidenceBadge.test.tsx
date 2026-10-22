import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConfidenceBadge } from "./ConfidenceBadge";

describe("image-reading provenance", () => {
  it("does not invent a confidence percentage for unscored readings", () => {
    render(<ConfidenceBadge source={{ type: "ocr", label: "이미지 판독", confidence: null }} />);
    expect(screen.getByText("이미지 판독")).toBeTruthy();
    expect(screen.queryByText(/%/)).toBeNull();
  });
});
