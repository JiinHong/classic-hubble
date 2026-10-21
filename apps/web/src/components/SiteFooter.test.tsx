import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SiteFooter } from "./SiteFooter";

describe("SiteFooter", () => {
  it("links the naming evidence and its open-data attribution", () => {
    render(<SiteFooter />);
    expect(
      screen.getByRole("link", { name: "작품명·별칭 출처" }).getAttribute("href"),
    ).toBe("/reference/korean-work-names.json");
    expect(
      screen.getByRole("link", { name: "CC BY-SA 4.0" }).getAttribute("href"),
    ).toBe("https://creativecommons.org/licenses/by-sa/4.0/");
  });

  it("credits the makers and shows the copyright", () => {
    render(<SiteFooter />);

    expect(screen.getByText("Classic Hubble by Jimin & Jinhong")).toBeTruthy();
    expect(
      screen.getByText("© 2026 Classic Hubble. All rights reserved."),
    ).toBeTruthy();
  });

  it("attributes KOPIS as the concert data provider", () => {
    render(<SiteFooter />);
    expect(
      screen
        .getByRole("link", { name: /공연예술통합전산망/ })
        .getAttribute("href"),
    ).toBe("https://www.kopis.or.kr");
  });
});
