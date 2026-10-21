import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SiteFooter } from "./SiteFooter";

describe("SiteFooter", () => {
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
