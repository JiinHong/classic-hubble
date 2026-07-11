import { performances } from "@classic-hubble/shared";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PerformanceCard } from "./PerformanceCard";

describe("PerformanceCard", () => {
  it("eagerly loads a poster when it is the leading card", () => {
    render(<PerformanceCard eager performance={performances[0]} />);

    expect(screen.getByRole("img").getAttribute("loading")).toBe("eager");
  });
});
