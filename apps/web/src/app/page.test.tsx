import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({
  getWorkSearchPage: vi.fn(async () => ({ works: [], performances: [], total: 0, hasMore: false })),
  getHomeOverview: vi.fn(async () => ({ performances: [], upcomingCount: 0, confirmedCount: 0 })),
  SearchExperience: vi.fn(() => <></>),
}));
vi.mock("@/components/SearchExperience", () => ({ SearchExperience: mocks.SearchExperience }));
vi.mock("@/lib/work-search", () => mocks);
import Home from "./page";
afterEach(() => vi.clearAllMocks());
describe("search-first home", () => {
  it("renders an empty search without downloading works, performances or counts", async () => {
    render(await Home({ searchParams: Promise.resolve({}) }));
    expect(mocks.getWorkSearchPage).not.toHaveBeenCalled();
    expect(mocks.getHomeOverview).not.toHaveBeenCalled();
    expect(mocks.SearchExperience).toHaveBeenCalled();
  });
  it("keeps composer entry links without doing an extra server search", async () => {
    render(await Home({ searchParams: Promise.resolve({ composer: ["라흐마니노프", "ignored"] }) }));
    expect(mocks.SearchExperience).toHaveBeenCalledWith(expect.objectContaining({ initialQuery: "라흐마니노프" }), undefined);
    expect(mocks.getWorkSearchPage).not.toHaveBeenCalled();
  });
  it("normalizes whitespace URLs to the empty home", async () => {
    render(await Home({ searchParams: Promise.resolve({ q: "   " }) }));
    expect(mocks.SearchExperience).toHaveBeenCalledWith(expect.objectContaining({ initialQuery: "" }), undefined);
    expect(mocks.getWorkSearchPage).not.toHaveBeenCalled();
  });
});
