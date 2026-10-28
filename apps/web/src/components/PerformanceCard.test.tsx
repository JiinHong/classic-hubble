import { performances } from "@classic-hubble/shared";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PerformanceCard } from "./PerformanceCard";

describe("PerformanceCard", () => {
  it("does not present an excerpt as a full-work performance", () => {
    const performance = { ...performances[0], program: [{ ...performances[0].program[0], performedScope: "excerpt" as const }] };
    render(<PerformanceCard performance={performance} />);
    expect(screen.getByText(/발췌/)).toBeTruthy();
    expect(screen.queryByText(/전곡/)).toBeNull();
  });
  it("eagerly loads a poster when it is the leading card", () => {
    render(<PerformanceCard eager performance={performances[0]} />);

    expect(screen.getByRole("img").getAttribute("loading")).toBe("eager");
  });

  it("includes the year when requested without changing the concert link", () => {
    render(<PerformanceCard showYear performance={{ ...performances[0], date: "2024-11-24", endDate: undefined }} />);
    expect(screen.getByText(/2024년 11월 24일/)).toBeTruthy();
    expect(screen.getByRole("link", { name: performances[0].title }).getAttribute("href")).toBe(`/performances/${performances[0].id}`);
  });
});
