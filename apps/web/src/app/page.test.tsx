import { performances, reviewQueue, works } from "@classic-hubble/shared";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  getCatalogSnapshot: vi.fn(),
  SearchExperience: vi.fn(() => null),
}));

vi.mock("@/components/SearchExperience", () => ({
  SearchExperience: mocks.SearchExperience,
}));

vi.mock("@/lib/catalog", () => ({
  getCatalogSnapshot: mocks.getCatalogSnapshot,
}));

import Home from "./page";

afterEach(() => {
  mocks.getCatalogSnapshot.mockReset();
  mocks.SearchExperience.mockClear();
});

describe("Home composer search params", () => {
  it("serializes only the first result page, never the whole catalog", async () => {
    const manyWorks = Array.from({ length: 1000 }, (_, i) => ({
      ...works[0],
      slug: `work-${i}`,
    }));
    mocks.getCatalogSnapshot.mockResolvedValue({
      works: manyWorks,
      performances: [],
      reviewQueue: [],
      source: "supabase",
    });
    render(await Home({ searchParams: Promise.resolve({}) }));
    const props = mocks.SearchExperience.mock.calls[0][0];
    expect(JSON.stringify(props).length).toBeLessThan(30_000);
    expect(props).toMatchObject({
      initialResult: { total: 1000, works: expect.any(Array) },
    });
    expect(
      (props as { initialResult: { works: unknown[] } }).initialResult.works,
    ).toHaveLength(24);
  });
  it("shows an outage instead of an empty search or sample claims", async () => {
    mocks.getCatalogSnapshot.mockResolvedValue({
      performances: [],
      works: [],
      reviewQueue: [],
      source: "unavailable",
    });
    render(await Home({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("alert").textContent).toContain(
      "공연 정보를 불러오지 못했습니다",
    );
    expect(mocks.SearchExperience).not.toHaveBeenCalled();
    expect(screen.queryByText("OCR 검수 대기")).toBeNull();
  });
  it.each([
    ["an absent composer", undefined, ""],
    [
      "a repeated composer",
      ["first composer", "second composer"],
      "first composer",
    ],
    ["a scalar composer", "세르게이 라흐마니노프", "세르게이 라흐마니노프"],
  ])(
    "passes %s to SearchExperience as initialQuery",
    async (_, composer, initialQuery) => {
      mocks.getCatalogSnapshot.mockResolvedValue({
        performances,
        reviewQueue,
        source: "fallback",
        works,
      });

      render(
        await Home({
          searchParams: Promise.resolve(
            composer === undefined ? {} : { composer },
          ),
        }),
      );

      expect(mocks.SearchExperience).toHaveBeenCalledWith(
        expect.objectContaining({ initialQuery }),
        undefined,
      );
    },
  );
});
