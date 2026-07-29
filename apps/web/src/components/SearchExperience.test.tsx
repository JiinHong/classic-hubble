import { performances, works } from "@classic-hubble/shared";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SearchExperience } from "./SearchExperience";

describe("SearchExperience composer deep link", () => {
  it("starts with the composer query and filters matching works", () => {
    render(
      <SearchExperience
        initialQuery="세르게이 라흐마니노프"
        performances={performances}
        works={works}
      />,
    );

    expect(
      (screen.getByLabelText("곡명, 작곡가, 공연장 검색") as HTMLInputElement)
        .value,
    ).toBe("세르게이 라흐마니노프");
    expect(screen.getByText("1개 작품 매칭")).toBeTruthy();
  });
});
