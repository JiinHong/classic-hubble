import { performances, works } from "@classic-hubble/shared";
import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ getCatalogWorkBySlug: vi.fn() }));
vi.mock("@/lib/catalog", () => mocks);
vi.mock("@/components/WatchlistButton", () => ({ WatchlistButton: () => null }));
vi.mock("next/navigation", () => ({ notFound: () => { throw new Error("NOT_FOUND"); } }));

import WorkPage from "./page";

afterEach(() => mocks.getCatalogWorkBySlug.mockReset());

const upcoming = { ...performances[0], id: "future", title: "Upcoming recital", date: "2099-12-01", endDate: undefined };
const historical = { ...performances[0], id: "PF253175", title: "노준탁 피아노 리사이틀 [전주]", date: "2024-11-24", endDate: undefined, status: "closed" as const };
const page = () => WorkPage({ params: Promise.resolve({ slug: works[0].slug }) });

describe("work performance history", () => {
  it("shows separate counts, year-bearing dates and navigable concerts in both sections", async () => {
    mocks.getCatalogWorkBySlug.mockResolvedValue({ work: works[0], performances: [upcoming], pastPerformances: [historical] });
    render(await page());
    const next = screen.getByRole("region", { name: "예정 공연" });
    const past = screen.getByRole("region", { name: "과거·종료 공연" });
    expect(within(next).getByText("1건")).toBeTruthy();
    expect(within(past).getByText("1건")).toBeTruthy();
    expect(within(next).getByRole("link", { name: upcoming.title }).getAttribute("href")).toBe("/performances/future");
    expect(within(past).getByRole("link", { name: historical.title }).getAttribute("href")).toBe("/performances/PF253175");
    expect(within(next).queryByText(historical.title)).toBeNull();
    expect(within(past).queryByText(upcoming.title)).toBeNull();
    expect(within(past).getByText(/2024년 11월 24일/)).toBeTruthy();
    expect(within(past).getByText("종료·취소")).toBeTruthy();
  });

  it("retains historical concerts when there are no upcoming concerts", async () => {
    mocks.getCatalogWorkBySlug.mockResolvedValue({ work: works[0], performances: [], pastPerformances: [historical] });
    render(await page());
    expect(screen.getByText("현재 확인된 예정 공연이 없습니다.")).toBeTruthy();
    expect(screen.getByRole("link", { name: historical.title })).toBeTruthy();
  });

  it("shows an independent empty state for each group", async () => {
    mocks.getCatalogWorkBySlug.mockResolvedValue({ work: works[0], performances: [], pastPerformances: [] });
    render(await page());
    expect(within(screen.getByRole("region", { name: "과거·종료 공연" })).getByText("연결된 과거·종료 공연이 없습니다.")).toBeTruthy();
    expect(screen.getByText("현재 확인된 예정 공연이 없습니다.")).toBeTruthy();
  });

  it("keeps missing works as not found", async () => {
    mocks.getCatalogWorkBySlug.mockResolvedValue({ work: null, performances: [], pastPerformances: [] });
    await expect(page()).rejects.toThrow("NOT_FOUND");
  });
});
