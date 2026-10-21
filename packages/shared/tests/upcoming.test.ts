import { describe, expect, it } from "vitest";
import { getUpcomingPerformancesFromList, performances } from "../src/index";

describe("upcoming performances", () => {
  it("excludes past and cancelled shows using the Korean calendar day", () => {
    const base = performances[0];
    const rows = [
      { ...base, id: "past", date: "2026-10-20" },
      { ...base, id: "today", date: "2026-10-21" },
      {
        ...base,
        id: "cancelled",
        date: "2026-10-22",
        status: "closed" as const,
      },
      { ...base, id: "running", date: "2026-10-19", endDate: "2026-10-23" },
    ];
    expect(
      getUpcomingPerformancesFromList(
        rows,
        new Date("2026-10-20T15:00:00Z"),
      ).map((p) => p.id),
    ).toEqual(["today", "running"]);
  });
});
