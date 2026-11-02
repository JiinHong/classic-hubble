import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SingleLineText } from "./SingleLineText";

let available = 150;
let natural = 300;
let resize: () => void;
const disconnect = vi.fn();
let fonts: EventTarget & { ready: Promise<void> };
const originalFonts = Object.getOwnPropertyDescriptor(document, "fonts");

beforeEach(() => {
  available = 150;
  natural = 300;
  disconnect.mockClear();
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(() => available);
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(() => ({ width: natural }) as DOMRect);
  vi.spyOn(window, "getComputedStyle").mockImplementation(() => ({ fontSize: "30px" }) as CSSStyleDeclaration);
  vi.stubGlobal("ResizeObserver", class {
    constructor(callback: () => void) { resize = callback; }
    observe() {}
    disconnect = disconnect;
  });
  fonts = Object.assign(new EventTarget(), { ready: Promise.resolve() });
  Object.defineProperty(document, "fonts", { configurable: true, value: fonts });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  if (originalFonts) Object.defineProperty(document, "fonts", originalFonts);
  else Reflect.deleteProperty(document, "fonts");
});

describe("single-line text fitting", () => {
  it("fits the full text to its own container without wrapping or ellipsis", () => {
    render(<SingleLineText>Full search prompt</SingleLineText>);
    const text = screen.getByText("Full search prompt");
    expect(text.style.fontSize).toBe("15px");
    expect(text.classList.contains("whitespace-nowrap")).toBe(true);
    expect(text.textContent).toBe("Full search prompt");
  });
  it("restores the inherited size when the container grows without enlarging it", () => {
    render(<SingleLineText>Prompt</SingleLineText>);
    available = 400;
    resize();
    expect(screen.getByText("Prompt").style.fontSize).toBe("");
    available = 100;
    resize();
    expect(screen.getByText("Prompt").style.fontSize).toBe("10px");
  });
  it("refits after fonts load and text changes", async () => {
    const { rerender } = render(<SingleLineText>Prompt</SingleLineText>);
    natural = 450;
    await fonts.ready;
    expect(screen.getByText("Prompt").style.fontSize).toBe("10px");
    natural = 600;
    fonts.dispatchEvent(new Event("loadingdone"));
    expect(screen.getByText("Prompt").style.fontSize).toBe("7.5px");
    natural = 150;
    rerender(<SingleLineText>Shorter</SingleLineText>);
    expect(screen.getByText("Shorter").style.fontSize).toBe("");
  });
  it("preserves accessibility attributes and releases observers on unmount", () => {
    const remove = vi.spyOn(fonts, "removeEventListener");
    const { unmount } = render(<SingleLineText aria-hidden="true" className="text-neutral-400">Prompt</SingleLineText>);
    expect(screen.getByText("Prompt").parentElement?.getAttribute("aria-hidden")).toBe("true");
    unmount();
    expect(disconnect).toHaveBeenCalledOnce();
    expect(remove).toHaveBeenCalledWith("loadingdone", expect.any(Function));
  });
  it("does not assign an invalid size to hidden or unmeasurable text", () => {
    available = 0;
    render(<SingleLineText>Prompt</SingleLineText>);
    expect(screen.getByText("Prompt").style.fontSize).toBe("");
    available = 100;
    natural = 0;
    resize();
    expect(screen.getByText("Prompt").style.fontSize).toBe("");
  });
});
