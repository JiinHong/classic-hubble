import { render, screen } from "@testing-library/react";
import { works } from "@classic-hubble/shared";
import { describe, expect, it } from "vitest";

import { WorkCard } from "./WorkCard";

describe("imported work metadata", () => {
  it("does not invent a popularity rank for imported works", () => {
    render(<WorkCard work={{ ...works[0], popularityRank: null }} />);
    expect(screen.queryByText(/^#/)).toBeNull();
  });
});
