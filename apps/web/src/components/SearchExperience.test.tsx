import { works, performances } from "@classic-hubble/shared";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { searchCatalog } from "@/lib/catalog-search";
import { SearchExperience } from "./SearchExperience";
const input = () => screen.getByRole("combobox", { name: "곡명, 작곡가, 별칭 검색" });
const welcome = () => screen.getByRole("heading", { name: "어떤 곡을 공연장에서 듣고 싶으세요?" });
const submit = (value: string) => { fireEvent.change(input(), { target: { value } }); fireEvent.keyDown(input(), { key: "Enter" }); };
beforeEach(() => { vi.useFakeTimers(); window.history.replaceState({}, "", "/"); });
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
async function settle() { await act(async () => { await vi.advanceTimersByTimeAsync(150); }); }
function renderSearch(query: string) {
  window.history.replaceState({}, "", `/?${new URLSearchParams({ q: query })}`);
  return render(<SearchExperience initialQuery={query} />);
}
function serve(data = { works, performances }) {
  const fetcher = vi.fn<typeof fetch>(async url => {
    const parsed = new URL(String(url), "https://example.com");
    const p = parsed.searchParams;
    if (parsed.pathname.endsWith("suggest")) return Response.json({ suggestions: [] });
    return Response.json(searchCatalog(data, { query: p.get("q") ?? "", mode: p.get("mode") === "performances" ? "performances" : "works", city: p.get("city") ?? "전체", offset: Number(p.get("offset") ?? 0) }));
  });
  vi.stubGlobal("fetch", fetcher); return fetcher;
}
describe("search-first experience", () => {
  it("shows a past-only result under its own heading, year and matching work", async () => {
    const concert = { ...performances[0], title: "공개 공연", id: "PFtest", date: "2024-05-11", program: [
      { ...performances[0].program[0], workSlug: "other", displayTitle: "다른 곡" },
      { ...performances[0].program[0], workSlug: "searched", displayTitle: "검색한 곡" }] };
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ works: [], performances: [concert],
      matchedWorkSlugs: { PFtest: "searched" }, periodCounts: { upcoming: 0, past: 1 }, total: 1, hasMore: false })));
    window.history.replaceState({}, "", "/?q=베토벤&mode=performances");
    render(<SearchExperience />); await settle();
    expect(screen.getByRole("heading", { name: /과거 공연/ })).toBeTruthy();
    expect(screen.getByRole("link", { name: "공개 공연" })).toBeTruthy();
    expect(screen.getByText(/2024년/)).toBeTruthy();
    expect(screen.getByText(/검색한 곡/)).toBeTruthy();
    expect(screen.queryByText(/다른 곡/)).toBeNull();
    expect(screen.queryByText("공연 정보 일치")).toBeNull();
    expect(screen.queryByText("검색 결과가 없습니다.")).toBeNull();
    fireEvent.change(screen.getByLabelText("기간"), { target: { value: "past" } }); await settle();
    expect(new URLSearchParams(location.search).get("period")).toBe("past");
  });
  it("restores the current URL when returning to a cached home with empty initial props", async () => {
    const fetcher = serve();
    window.history.replaceState({}, "", "/?q=운명&work=beethoven-symphony-5");
    render(<SearchExperience />); await settle();
    expect((input() as HTMLInputElement).value).toBe("운명");
    expect(fetcher.mock.calls.some(([u]) => String(u).includes("/selected-work?work=beethoven-symphony-5"))).toBe(true);
  });
  it("starts with only a search box and does not request the catalog", async () => {
    const fetcher = serve(); render(<SearchExperience />); await settle();
    expect(welcome()).toBeTruthy();
    expect(screen.queryByText("등록된 공연")).toBeNull(); expect(fetcher).not.toHaveBeenCalled();
  });
  it("plays the welcome entrance once and removes it when finished", () => {
    serve(); render(<SearchExperience />);
    expect(welcome().classList.contains("search-welcome-enter")).toBe(true);
    // jsdom lacks AnimationEvent, so React registers the WebKit fallback.
    fireEvent(welcome(), new Event("webkitAnimationEnd", { bubbles: true }));
    expect(welcome().classList.contains("search-welcome-enter")).toBe(false);
  });
  it("does not replay the entrance after searching and clearing before it finishes", async () => {
    serve(); render(<SearchExperience />);
    submit("운명"); await settle();
    fireEvent.click(screen.getByRole("button", { name: "검색어 지우기" })); await settle();
    expect(welcome().classList.contains("search-welcome-enter")).toBe(false);
  });
  it("does not play the entrance when clearing a search opened by URL", async () => {
    serve(); renderSearch("운명"); await settle();
    fireEvent.click(screen.getByRole("button", { name: "검색어 지우기" })); await settle();
    expect(welcome().classList.contains("search-welcome-enter")).toBe(false);
  });
  it("submits only on Enter, updates URL and restores the empty home on clear", async () => {
    const fetcher = serve(); render(<SearchExperience />);
    fireEvent.change(input(), { target: { value: "운명" } }); await settle();
    expect(fetcher.mock.calls.every(([u]) => String(u).includes("/suggest?"))).toBe(true);
    fireEvent.keyDown(input(), { key: "Enter" }); await settle();
    expect(screen.getByRole("link", { name: /교향곡 5번/ })).toBeTruthy();
    expect(new URLSearchParams(location.search).get("q")).toBe("운명");
    fireEvent.click(screen.getByRole("button", { name: "검색어 지우기" })); await settle();
    expect(location.search).toBe(""); expect(screen.queryByRole("link", { name: /교향곡 5번/ })).toBeNull();
  });
  it("uses exact suggestion identity and keeps a link to the full work history", async () => {
    const fetcher = serve();
    fetcher.mockImplementation(async url => String(url).includes("/suggest?") ? Response.json({ suggestions: [{ slug: "exact-work", title: "선택 작품", composer: "작곡가" }] }) : Response.json({ works: [{ ...works[0], slug: "exact-work" }], performances: [], total: 0, hasMore: false }));
    render(<SearchExperience />);
    fireEvent.change(input(), { target: { value: "선택" } }); await settle();
    fireEvent.click(screen.getByRole("option")); await settle();
    expect(fetcher.mock.calls.some(([u]) => String(u).includes("/selected-work?work=exact-work"))).toBe(true);
    expect(screen.getByRole("link", { name: "작품과 과거 공연" }).getAttribute("href")).toBe("/works/exact-work");
  });
  it("keeps the input focused when a submitted search is cleared for the next search", async () => {
    serve(); renderSearch("운명"); await settle();
    const field = input();
    act(() => field.focus());
    fireEvent.change(field, { target: { value: "" } }); await settle();
    expect(input()).toBe(field);
    expect(document.activeElement).toBe(field);
    fireEvent.change(field, { target: { value: "신세계" } });
    fireEvent.click(screen.getByRole("button", { name: "검색어 지우기" })); await settle();
    expect(document.activeElement).toBe(field);
    expect((field as HTMLInputElement).value).toBe("");
  });
  it("keeps previous committed query separate while a new draft is typed", async () => {
    serve(); renderSearch("운명"); await settle();
    fireEvent.change(input(), { target: { value: "신세계" } }); await settle();
    expect(screen.getByRole("heading", { name: "운명" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /교향곡 5번/ })).toBeTruthy();
  });
  it("restores browser navigation without repeating a fresh result request", async () => {
    const fetcher = serve(); render(<SearchExperience />);
    submit("운명"); await settle(); submit("신세계"); await settle();
    const before = fetcher.mock.calls.filter(([u]) => String(u).includes("/search?")).length;
    window.history.replaceState({}, "", "/?q=운명");
    fireEvent(window, new PopStateEvent("popstate")); await settle();
    expect((input() as HTMLInputElement).value).toBe("운명");
    expect(fetcher.mock.calls.filter(([u]) => String(u).includes("/search?")).length).toBe(before);
  });
  it("appends pages once and resets paging on a new submitted query", async () => {
    const many = Array.from({ length: 30 }, (_, i) => ({ ...works[0], slug: `w${i}`, title: `Composition ${i + 1}`, titleKo: `Composition ${i + 1}` }));
    serve({ works: many, performances: [] }); renderSearch("Composition"); await settle();
    expect(screen.queryByRole("link", { name: /Composition 30$/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "작품 더 보기" })); await settle();
    expect(screen.getAllByRole("link", { name: /Composition \d+$/ })).toHaveLength(30);
    submit("Composition 30"); await settle();
    expect(screen.getAllByRole("link", { name: /Composition \d+$/ })).toHaveLength(1);
  });
  it("distinguishes failure from no matches and retries", async () => {
    const fetcher = serve(); fetcher.mockResolvedValueOnce(Response.json({}, { status: 503 }));
    renderSearch("운명"); await settle();
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.queryByText("검색 결과가 없습니다.")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" })); await settle();
    expect(screen.getByRole("link", { name: /교향곡 5번/ })).toBeTruthy();
  });
  it("refreshes expired cached results", async () => {
    const fetcher = serve(); render(<SearchExperience />);
    submit("운명"); await settle(); submit("신세계"); await settle();
    await act(async () => { vi.advanceTimersByTime(60_001); });
    submit("운명"); await settle();
    expect(fetcher.mock.calls.filter(([u]) => String(u).includes("/search?")).length).toBe(3);
  });
  it("never replaces a newer submitted query with a stale response", async () => {
    const fetcher = serve(); let resolve!: (r: Response) => void;
    fetcher.mockImplementationOnce(() => new Promise(r => { resolve = r; }));
    renderSearch("운명"); await settle();
    submit("신세계"); await settle();
    await act(async () => resolve(Response.json(searchCatalog({ works, performances }, { query: "운명" }))));
    expect(screen.queryByRole("link", { name: /교향곡 5번/ })).toBeNull();
    expect(screen.getByRole("link", { name: /교향곡 9번/ })).toBeTruthy();
  });
});
