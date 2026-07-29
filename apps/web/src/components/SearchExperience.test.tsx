import { performances, works } from "@classic-hubble/shared";
import { fireEvent, render, screen } from "@testing-library/react";
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

  it("shows every performance linked to a work matching a Korean composer query", () => {
    render(
      <SearchExperience
        initialQuery="세르게이 라흐마니노프"
        performances={performances}
        works={works}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "공연" }));

    expect(screen.getByText("2개 공연 매칭")).toBeTruthy();
    expect(
      screen.getByText("김정원과 친구들 - 저먼 로맨틱스"),
    ).toBeTruthy();
    expect(
      screen.getByText("2026 서초국제예술단 피아노 갈라 콘서트"),
    ).toBeTruthy();
  });
});
