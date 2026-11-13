import { act, fireEvent, render, screen } from "@testing-library/react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SearchBox } from "./SearchBox";
vi.mock("@/data/starter-suggestions.json", () => ({ default: { "베토": [
  { slug: "work-a", title: "교향곡", composer: "베토벤" },
] } }));
const suggestion = { slug: "exact-work", title: "피아노 협주곡 2번", composer: "라흐마니노프" };
beforeEach(() => vi.useFakeTimers());
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
async function settle() { await act(async () => { await vi.advanceTimersByTimeAsync(120); }); }
function setup() {
  const onSubmit = vi.fn(), onSelect = vi.fn(), onClear = vi.fn();
  const fetcher = vi.fn<typeof fetch>(async () => Response.json({ suggestions: [suggestion] }));
  vi.stubGlobal("fetch", fetcher);
  render(<SearchBox initialValue="" onSubmit={onSubmit} onSelect={onSelect} onClear={onClear} onVideo={vi.fn()} />);
  const input = screen.getByRole("combobox");
  fireEvent.focus(input);
  return { input, onSubmit, onSelect, onClear, fetcher };
}
describe("autocomplete search input", () => {
  it("adopts a draft typed into the server HTML before hydration", async () => {
    const box = <SearchBox initialValue="" onSubmit={vi.fn()} onSelect={vi.fn()} onClear={vi.fn()} onVideo={vi.fn()} />;
    const host = document.body.appendChild(document.createElement("div"));
    host.innerHTML = renderToString(box);
    const field = host.querySelector("input")!;
    field.focus();
    field.value = "베토";
    const root = await act(() => hydrateRoot(host, box));
    try {
      expect(field.value).toBe("베토");
      expect(screen.getByRole("option").textContent).toContain("베토벤");
      expect(document.activeElement).toBe(field);
    } finally {
      await act(() => root.unmount());
      host.remove();
    }
  });
  it("renders a prepared prefix before any timer and revalidates the order", async () => {
    const { input, fetcher } = setup();
    fireEvent.change(input, { target: { value: "베토" } });
    expect(screen.getByRole("option").textContent).toContain("베토벤");
    expect(fetcher).not.toHaveBeenCalled();
    await settle();
    expect(screen.getByRole("option").textContent).toContain(suggestion.title);
  });
  it("keeps only compatible candidates while extending a draft, never an unrelated one", async () => {
    const { input } = setup();
    fireEvent.change(input, { target: { value: "라" } }); await settle();
    fireEvent.change(input, { target: { value: "라흐마" } });
    expect(screen.getByRole("option").textContent).toContain("라흐마니노프");
    fireEvent.change(input, { target: { value: "다른" } });
    expect(screen.queryByRole("option")).toBeNull();
  });
  it("preserves a keyboard choice by identity when live suggestions reorder it", async () => {
    const { input, fetcher, onSelect } = setup();
    const seed = { slug: "work-a", title: "교향곡", composer: "베토벤" };
    fetcher.mockResolvedValueOnce(Response.json({ suggestions: [suggestion, seed] }));
    fireEvent.change(input, { target: { value: "베토" } });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    await settle();
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith(seed);
  });
  it("does not keep prepared candidates after a successful empty response", async () => {
    const { input, fetcher } = setup();
    fetcher.mockResolvedValueOnce(Response.json({ suggestions: [] }));
    fireEvent.change(input, { target: { value: "베토" } });
    await settle();
    expect(screen.queryByRole("option")).toBeNull();
    expect(screen.getByRole("status").textContent).toContain("없습니다");
  });
  it("invites searches by classical work title or composer", () => {
    const { input } = setup();
    expect(input.getAttribute("placeholder")).toBe("클래식 곡명이나 작곡가를 입력하세요");
    const prompt = screen.getByText("클래식 곡명이나 작곡가를 입력하세요");
    expect(prompt.parentElement?.getAttribute("aria-hidden")).toBe("true");
    expect(prompt.classList.contains("whitespace-nowrap")).toBe(true);
    fireEvent.change(input, { target: { value: "라흐" } });
    expect(screen.queryByText("클래식 곡명이나 작곡가를 입력하세요")).toBeNull();
  });
  it("keeps the search accessible without a leading magnifier", () => {
    const { input } = setup();
    const form = screen.getByRole("search");
    expect(form.querySelector(".lucide-search")).toBeNull();
    expect(form.firstElementChild?.contains(input)).toBe(true);
    expect(input.getAttribute("aria-label")).toBe("곡명, 작곡가, 별칭 검색");
    const toggle = screen.getByRole("button", { name: "유튜브로 찾기" });
    fireEvent.click(toggle);
    expect(input.getAttribute("placeholder")).toBe("마음에 드는 클래식 음악의 유튜브 링크를 넣어보세요");
    expect(toggle.getAttribute("aria-pressed")).toBe("true");
    expect(document.activeElement).toBe(input);
    fireEvent.click(toggle);
    expect(input.getAttribute("placeholder")).toBe("클래식 곡명이나 작곡가를 입력하세요");
  });
  it("uses a capsule field and a circular submit button", () => {
    setup();
    expect(screen.getByRole("search").classList.contains("rounded-full")).toBe(true);
    expect(screen.getByRole("button", { name: /^검색$/ }).classList.contains("rounded-full")).toBe(true);
  });
  it("changes the hint without erasing the user's draft", () => {
    const { input, onClear } = setup();
    fireEvent.change(input, { target: { value: "베토벤" } });
    fireEvent.click(screen.getByRole("button", { name: "유튜브로 찾기" }));
    expect((input as HTMLInputElement).value).toBe("베토벤");
    expect(onClear).not.toHaveBeenCalled();
  });
  it("only fetches lightweight suggestions while typing; Enter submits the draft", async () => {
    const { input, fetcher, onSubmit } = setup();
    fireEvent.change(input, { target: { value: "라흐" } });
    expect(fetcher).not.toHaveBeenCalled();
    await settle();
    expect(fetcher.mock.calls[0][0]).toContain("/api/catalog/suggest?");
    expect(onSubmit).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledWith("라흐");
  });
  it("selects an exact identity with arrow keys, not a reconstructed query", async () => {
    const { input, onSelect, onSubmit } = setup();
    fireEvent.change(input, { target: { value: "라흐" } }); await settle();
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith(suggestion);
    expect(onSubmit).not.toHaveBeenCalled();
  });
  it("keeps the active keyboard suggestion in view", async () => {
    const { input } = setup();
    fireEvent.change(input, { target: { value: "라흐" } }); await settle();
    const scroll = vi.fn();
    screen.getByRole("option").scrollIntoView = scroll;
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(scroll).toHaveBeenCalledWith({ block: "nearest" });
  });
  it("shows debounced recommendations during Korean composition without submitting", async () => {
    const { input, fetcher, onSubmit, onSelect } = setup();
    fireEvent.compositionStart(input);
    fireEvent.change(input, { target: { value: "운" } });
    fireEvent.change(input, { target: { value: "운명" } }); await settle();
    expect(fetcher).toHaveBeenCalledOnce();
    expect(new URL(String(fetcher.mock.calls[0][0]), "https://example.com").searchParams.get("q")).toBe("운명");
    expect(screen.getByRole("option")).toBeTruthy();
    fireEvent.keyDown(input, { key: "ArrowDown", isComposing: true });
    fireEvent.keyDown(input, { key: "Enter", isComposing: true, keyCode: 229 });
    expect(onSelect).not.toHaveBeenCalled(); expect(onSubmit).not.toHaveBeenCalled();
    fireEvent.compositionEnd(input); await settle();
    expect(fetcher).toHaveBeenCalledOnce();
    fireEvent.keyDown(input, { key: "Enter", keyCode: 229 });
    expect(onSubmit).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith(suggestion);
  });
  it("shows no loading text or empty popup while recommendations are pending", async () => {
    const { input, fetcher } = setup();
    let resolve!: (response: Response) => void;
    fetcher.mockImplementationOnce(() => new Promise(r => { resolve = r; }));
    fireEvent.change(input, { target: { value: "Beethoven" } }); await settle();
    expect(screen.queryByText("검색 중")).toBeNull();
    expect(screen.queryByRole("listbox")).toBeNull();
    expect(input.getAttribute("aria-expanded")).toBe("false");
    await act(async () => resolve(Response.json({ suggestions: [suggestion] })));
    expect(screen.getByRole("option")).toBeTruthy();
    expect(input.getAttribute("aria-expanded")).toBe("true");
  });
  it.each(["select", "clear"])("resets composition after a pointer %s so the next search can submit", async action => {
    const { input, onSubmit } = setup();
    fireEvent.compositionStart(input);
    fireEvent.change(input, { target: { value: "운명" } }); await settle();
    if (action === "select") fireEvent.click(screen.getByRole("option"));
    else fireEvent.click(screen.getByRole("button", { name: "검색어 지우기" }));
    fireEvent.change(input, { target: { value: "Beethoven" } }); await settle();
    expect((screen.getByRole("button", { name: /^검색$/ }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledWith("Beethoven");
  });
  it("hides stale recommendations until the new Korean draft resolves", async () => {
    const { input, fetcher } = setup();
    fireEvent.change(input, { target: { value: "운명" } }); await settle();
    expect(screen.getByRole("option")).toBeTruthy();
    let resolve!: (response: Response) => void;
    fetcher.mockImplementationOnce(() => new Promise(r => { resolve = r; }));
    fireEvent.compositionStart(input);
    fireEvent.change(input, { target: { value: "신세계" } }); await settle();
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("listbox")).toBeNull();
    await act(async () => resolve(Response.json({ suggestions: [{ ...suggestion, title: "교향곡 9번" }] })));
    expect(screen.getByRole("option").textContent).toContain("교향곡 9번");
    expect(screen.queryByText(suggestion.title)).toBeNull();
  });
  it("closes on Escape and clears without fetching an empty catalog", async () => {
    const { input, onClear, fetcher } = setup();
    fireEvent.change(input, { target: { value: "운명" } }); await settle();
    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("listbox")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "검색어 지우기" })); await settle();
    expect(onClear).toHaveBeenCalledOnce(); expect(fetcher).toHaveBeenCalledOnce();
  });
  it("reuses recent suggestions and rejects an old response", async () => {
    const { input, fetcher } = setup();
    fireEvent.change(input, { target: { value: "운명" } }); await settle();
    let resolve!: (r: Response) => void;
    fetcher.mockImplementationOnce(() => new Promise(r => { resolve = r; }));
    fireEvent.change(input, { target: { value: "old" } }); await settle();
    fireEvent.change(input, { target: { value: "운명" } }); await settle();
    await act(async () => resolve(Response.json({ suggestions: [{ ...suggestion, title: "OLD" }] })));
    expect(screen.queryByText("OLD")).toBeNull(); expect(fetcher).toHaveBeenCalledTimes(2);
  });
  it("keeps normal submission available after suggestions fail", async () => {
    const { input, fetcher, onSubmit } = setup();
    fetcher.mockResolvedValueOnce(Response.json({}, { status: 503 }));
    fireEvent.change(input, { target: { value: "unknown" } }); await settle();
    expect(screen.getByRole("alert")).toBeTruthy();
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledWith("unknown");
  });
  it("clears a submitted search when its draft becomes whitespace", async () => {
    const { input, onClear, fetcher } = setup();
    fireEvent.change(input, { target: { value: "   " } }); await settle();
    expect(onClear).toHaveBeenCalledOnce(); expect(fetcher).not.toHaveBeenCalled();
  });
});
