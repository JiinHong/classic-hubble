import { performances, reviewQueue, works } from "@classic-hubble/shared";
import { render } from "@testing-library/react";
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
  it.each([
    ["an absent composer", undefined, ""],
    ["a repeated composer", ["first composer", "second composer"], "first composer"],
    ["a scalar composer", "세르게이 라흐마니노프", "세르게이 라흐마니노프"],
  ])("passes %s to SearchExperience as initialQuery", async (_, composer, initialQuery) => {
    mocks.getCatalogSnapshot.mockResolvedValue({
      performances,
      reviewQueue,
      source: "fallback",
      works,
    });

    render(
      await Home({
        searchParams: Promise.resolve(composer === undefined ? {} : { composer }),
      }),
    );

    expect(mocks.SearchExperience).toHaveBeenCalledWith(
      expect.objectContaining({ initialQuery }),
      undefined,
    );
  });
});
