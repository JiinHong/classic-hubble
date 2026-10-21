import { performances, works } from "@classic-hubble/shared";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SearchExperience } from "./SearchExperience";

describe("SearchExperience composer deep link", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-07-01T00:00:00Z"));
  });
  afterEach(() => vi.useRealTimers());
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
    expect(screen.getByText("김정원과 친구들 - 저먼 로맨틱스")).toBeTruthy();
    expect(
      screen.getByText("2026 서초국제예술단 피아노 갈라 콘서트"),
    ).toBeTruthy();
  });

  it("shows performances in batches and resets the batch when searching", () => {
    const manyPerformances = Array.from({ length: 30 }, (_, index) => ({
      ...performances[0],
      id: `performance-${index}`,
      title: `Concert ${index + 1}`,
    }));
    render(<SearchExperience performances={manyPerformances} works={works} />);
    fireEvent.click(screen.getByRole("button", { name: "공연", exact: true }));
    expect(screen.getByText("30개 공연 매칭")).toBeTruthy();
    expect(screen.getByText("Concert 24")).toBeTruthy();
    expect(screen.queryByText("Concert 25")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "공연 더 보기" }));
    expect(screen.getByText("Concert 30")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "공연 더 보기" })).toBeNull();
    fireEvent.change(screen.getByLabelText("곡명, 작곡가, 공연장 검색"), {
      target: { value: "Concert" },
    });
    expect(screen.queryByText("Concert 25")).toBeNull();
  });

  it("explicitly shows an empty search instead of a blank result area", () => {
    render(
      <SearchExperience initialQuery="없는곡" performances={[]} works={[]} />,
    );
    expect(screen.getByText("검색 결과가 없습니다.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "공연", exact: true }));
    expect(screen.getByText("검색 결과가 없습니다.")).toBeTruthy();
  });
});
