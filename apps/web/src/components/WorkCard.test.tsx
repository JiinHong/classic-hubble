import { render, screen } from "@testing-library/react";
import { works } from "@classic-hubble/shared";
import { describe, expect, it } from "vitest";

import { WorkCard } from "./WorkCard";

describe("imported work metadata", () => {
  it("does not invent a popularity rank for imported works", () => {
    render(<WorkCard work={{ ...works[0], popularityRank: null }} />);
    expect(screen.queryByText(/^#/)).toBeNull();
  });
  it("shows the parent and piece number without counting its performances", () => {
    render(<WorkCard work={{ ...works[0], titleKo: "고독한 꽃", upcomingPerformanceIds: [],
      partOf: [{ slug: "forest-scenes", title: "Waldszenen", titleKo: "숲의 정경", catalogue: "Op. 82", position: 3 }] }} />);
    expect(screen.getByRole("link", { name: "숲의 정경 · 3번 수록곡" }).getAttribute("href")).toBe("/works/forest-scenes");
    expect(screen.getByText("예정 공연 0건")).not.toBeNull();
  });
});
