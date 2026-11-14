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
  it.each(["performances", "pastPerformances"] as const)("shows the selected work instead of the opening piece in %s", async (group) => {
    const selected = {
      ...performances[0].program[0],
      workSlug: works[0].slug,
      displayTitle: "Selected work excerpt",
      composerName: "Selected composer",
      performedScope: "excerpt" as const,
      source: { type: "ocr" as const, label: "OCR 근거 확인", confidence: null },
    };
    const opening = {
      ...selected,
      workSlug: "different-work",
      displayTitle: "Unrelated opening piece",
      composerName: "Different composer",
      performedScope: "full_work" as const,
      source: { type: "official" as const, label: "Official", confidence: null },
    };
    const concert = { ...historical, program: [opening, selected] };
    mocks.getCatalogWorkBySlug.mockResolvedValue({ cancelledPerformances: [], unavailablePerformances: [], work: works[0], performances: [], pastPerformances: [], [group]: [concert] });

    render(await page());

    expect(screen.getByText("Selected composer · Selected work excerpt · 발췌")).toBeTruthy();
    expect(screen.queryByText("OCR 근거 확인")).toBeNull();
    for (const label of ["편성", "작품 정보 출처", "검색 별칭"]) expect(screen.queryByText(label)).toBeNull();
    expect(screen.queryByText(/Unrelated opening piece/)).toBeNull();
    expect(concert.program).toEqual([opening, selected]);
  });

  it("shows separate counts, year-bearing dates and navigable concerts in both sections", async () => {
    mocks.getCatalogWorkBySlug.mockResolvedValue({ cancelledPerformances: [], unavailablePerformances: [], work: works[0], performances: [upcoming], pastPerformances: [historical] });
    render(await page());
    const next = screen.getByRole("region", { name: "예정 공연" });
    const past = screen.getByRole("region", { name: "지난 공연" });
    expect(within(next).getByText("1건")).toBeTruthy();
    expect(within(past).getByText("1건")).toBeTruthy();
    expect(within(next).getByRole("link", { name: upcoming.title }).getAttribute("href")).toBe("/performances/future");
    expect(within(past).getByRole("link", { name: historical.title }).getAttribute("href")).toBe("/performances/PF253175");
    expect(within(next).queryByText(historical.title)).toBeNull();
    expect(within(past).queryByText(upcoming.title)).toBeNull();
    expect(within(past).getByText(/2024년 11월 24일/)).toBeTruthy();
    expect(within(past).queryByText(/취소/)).toBeNull();
  });

  it("keeps confirmed cancellations out of the past list", async () => {
    const cancelled = { ...historical, id: "cancel", title: "취소된 리사이틀", cancelled: true };
    mocks.getCatalogWorkBySlug.mockResolvedValue({ work: works[0], performances: [], pastPerformances: [historical], cancelledPerformances: [cancelled], unavailablePerformances: [] });
    render(await page());
    const section = screen.getByRole("region", { name: "취소된 공연" });
    expect(within(section).getByText("공연 취소")).toBeTruthy();
    expect(within(section).getByRole("link", { name: cancelled.title })).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "지난 공연" })).queryByText(cancelled.title)).toBeNull();
  });

  it("retains historical concerts when there are no upcoming concerts", async () => {
    mocks.getCatalogWorkBySlug.mockResolvedValue({ cancelledPerformances: [], unavailablePerformances: [], work: works[0], performances: [], pastPerformances: [historical] });
    render(await page());
    expect(screen.getByText("현재 확인된 예정 공연이 없습니다.")).toBeTruthy();
    expect(screen.getByRole("link", { name: historical.title })).toBeTruthy();
  });

  it("shows an independent empty state for each group", async () => {
    mocks.getCatalogWorkBySlug.mockResolvedValue({ cancelledPerformances: [], unavailablePerformances: [], work: works[0], performances: [], pastPerformances: [] });
    render(await page());
    expect(within(screen.getByRole("region", { name: "지난 공연" })).getByText("아직 지난 공연이 없습니다.")).toBeTruthy();
    expect(screen.getByText("현재 확인된 예정 공연이 없습니다.")).toBeTruthy();
  });

  it("keeps missing works as not found", async () => {
    mocks.getCatalogWorkBySlug.mockResolvedValue({ cancelledPerformances: [], unavailablePerformances: [], work: null, performances: [], pastPerformances: [] });
    await expect(page()).rejects.toThrow("NOT_FOUND");
  });
});
