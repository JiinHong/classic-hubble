import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SiteFooter } from "./SiteFooter";

describe("SiteFooter", () => {
  it("credits the makers and shows the copyright", () => {
    render(<SiteFooter />);

    expect(
      screen.getByText("Classic Hubble by Jimin & Jinhong"),
    ).toBeTruthy();
    expect(
      screen.getByText("© 2026 Classic Hubble. All rights reserved."),
    ).toBeTruthy();
  });
});
