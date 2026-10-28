import { performances, works } from "@classic-hubble/shared";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { searchCatalog } from "@/lib/catalog-search";
import { SearchExperience } from "./SearchExperience";

const catalog = { performances, works };
const input = () => screen.getByLabelText("곡명, 작곡가, 공연장 검색");
beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-07-01T00:00:00Z"));
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
async function settle() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(300);
  });
}
function serve(data = catalog) {
  const fetcher = vi.fn(async (url: string) => {
    const params = new URL(url, "https://example.com").searchParams;
    return Response.json(
      searchCatalog(data, {
        query: params.get("q") ?? "",
        mode: params.get("mode") === "performances" ? "performances" : "works",
        city: params.get("city") ?? "전체",
        offset: Number(params.get("offset") ?? 0),
      }),
    );
  });
  vi.stubGlobal("fetch", fetcher);
  return fetcher;
}

describe("paginated catalog search", () => {
  it("reuses recent results when returning to a query, without another request", async () => {
    const fetcher = serve();
    render(<SearchExperience initialResult={searchCatalog(catalog, {})} />);
    fireEvent.change(input(), { target: { value: "운명" } });
    await settle();
    fireEvent.change(input(), { target: { value: "신세계" } });
    await settle();
    expect(fetcher).toHaveBeenCalledTimes(2);
    fireEvent.change(input(), { target: { value: "운명" } });
    await settle();
    expect(screen.getByText("1개 작품 매칭")).toBeTruthy();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
  it("refreshes expired search results instead of keeping stale concerts indefinitely", async () => {
    const fetcher = serve();
    render(<SearchExperience initialResult={searchCatalog(catalog, {})} />);
    fireEvent.change(input(), { target: { value: "운명" } });
    await settle();
    fireEvent.change(input(), { target: { value: "신세계" } });
    await settle();
    await act(async () => vi.advanceTimersByTime(60_001));
    fireEvent.change(input(), { target: { value: "운명" } });
    await settle();
    expect(fetcher).toHaveBeenCalledTimes(3);
  });
  it("recovers when clearing a failed query back to the initial search", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          Response.json({ error: "unavailable" }, { status: 503 }),
        )
        .mockImplementation(async () =>
          Response.json(searchCatalog(catalog, {})),
        ),
    );
    render(<SearchExperience initialResult={searchCatalog(catalog, {})} />);
    fireEvent.change(input(), { target: { value: "failed query" } });
    await settle();
    expect(screen.getByRole("alert")).toBeTruthy();
    fireEvent.change(input(), { target: { value: "" } });
    await settle();
    expect(screen.getByText(`${works.length}개 작품 매칭`)).toBeTruthy();
  });
  it("starts with server-rendered composer results without repeating the request", async () => {
    const fetcher = serve();
    render(
      <SearchExperience
        initialQuery="세르게이 라흐마니노프"
        initialResult={searchCatalog(catalog, {
          query: "세르게이 라흐마니노프",
        })}
      />,
    );
    expect((input() as HTMLInputElement).value).toBe("세르게이 라흐마니노프");
    expect(screen.getByText("1개 작품 매칭")).toBeTruthy();
    await settle();
    expect(fetcher).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /^공연$/ }));
    await settle();
    expect(screen.getByText("2개 공연 매칭")).toBeTruthy();
    expect(screen.getByText("김정원과 친구들 - 저먼 로맨틱스")).toBeTruthy();
  });
  it("loads the next page and searches works not present in the browser", async () => {
    const many = Array.from({ length: 30 }, (_, i) => ({
      ...works[0],
      slug: `w${i}`,
      titleKo: `Composition ${i + 1}`,
      title: `Composition ${i + 1}`,
    }));
    serve({ works: many, performances: [] });
    render(
      <SearchExperience
        initialResult={searchCatalog({ works: many, performances: [] }, {})}
      />,
    );
    expect(screen.queryByRole("link", { name: /Composition 30$/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "작품 더 보기" }));
    await settle();
    expect(screen.getByRole("link", { name: /Composition 30$/ })).toBeTruthy();
    fireEvent.change(input(), { target: { value: "Composition 30" } });
    await settle();
    expect(screen.getByText("1개 작품 매칭")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Composition 30$/ })).toBeTruthy();
  });
  it("reuses cached pages without duplicating appended results", async () => {
    const many = Array.from({ length: 30 }, (_, i) => ({
      ...works[0],
      slug: `w${i}`,
      title: `Composition ${i + 1}`,
      titleKo: `Composition ${i + 1}`,
    }));
    const data = { works: many, performances: [] };
    const fetcher = serve(data);
    render(<SearchExperience initialResult={searchCatalog(data, {})} />);
    fireEvent.change(input(), { target: { value: "Composition" } });
    await settle();
    fireEvent.click(screen.getByRole("button", { name: "작품 더 보기" }));
    await settle();
    fireEvent.change(input(), { target: { value: "Composition 30" } });
    await settle();
    fireEvent.change(input(), { target: { value: "Composition" } });
    await settle();
    fireEvent.click(screen.getByRole("button", { name: "작품 더 보기" }));
    await settle();
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(
      screen.getAllByRole("link", { name: /Composition \d+$/ }),
    ).toHaveLength(30);
    expect(screen.queryByRole("button", { name: "작품 더 보기" })).toBeNull();
  });
  it("debounces typing and prevents an older response replacing a newer search", async () => {
    let resolve!: (response: Response) => void;
    const fetcher = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<Response>((done) => {
            resolve = done;
          }),
      )
      .mockResolvedValue(
        Response.json({
          works: [],
          performances: [],
          total: 0,
          hasMore: false,
        }),
      );
    vi.stubGlobal("fetch", fetcher);
    render(<SearchExperience initialResult={searchCatalog(catalog, {})} />);
    fireEvent.change(input(), { target: { value: "old" } });
    await settle();
    fireEvent.change(input(), { target: { value: "n" } });
    fireEvent.change(input(), { target: { value: "new" } });
    await settle();
    expect(fetcher).toHaveBeenCalledTimes(2);
    await act(async () => resolve(Response.json(searchCatalog(catalog, {}))));
    expect(screen.getByText("검색 결과가 없습니다.")).toBeTruthy();
  });
  it("distinguishes a failed request from no matches and supports retry", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        Response.json({ error: "unavailable" }, { status: 503 }),
      )
      .mockResolvedValue(
        Response.json({
          works: [],
          performances: [],
          total: 0,
          hasMore: false,
        }),
      );
    vi.stubGlobal("fetch", fetcher);
    render(<SearchExperience initialResult={searchCatalog(catalog, {})} />);
    fireEvent.change(input(), { target: { value: "unknown" } });
    await settle();
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.queryByText("검색 결과가 없습니다.")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    await settle();
    expect(screen.getByText("검색 결과가 없습니다.")).toBeTruthy();
  });
});
