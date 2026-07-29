import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { toComposerDirectoryEntry } from "@/lib/composer-directory";

import { ComposerDirectory } from "./ComposerDirectory";

const composers = [
  toComposerDirectoryEntry({
    id: "bach",
    name: "Johann Sebastian Bach",
    nameKo: "요한 제바스티안 바흐",
    period: "Baroque",
  }),
  toComposerDirectoryEntry({
    id: "vivaldi",
    name: "Antonio Vivaldi",
    nameKo: "안토니오 비발디",
    period: "Baroque",
  }),
  toComposerDirectoryEntry({
    id: "debussy",
    name: "Claude Debussy",
    nameKo: "클로드 드뷔시",
    period: "20th Century",
  }),
];

function composerHref(nameKo: string) {
  return `/?composer=${encodeURIComponent(nameKo)}`;
}

describe("ComposerDirectory", () => {
  it("shows all composers with Korean and original names", () => {
    render(<ComposerDirectory composers={composers} />);

    expect(screen.getByText("3명의 작곡가")).toBeTruthy();
    expect(screen.getAllByText("요한 제바스티안 바흐").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Johann Sebastian Bach").length).toBeGreaterThan(
      0,
    );
  });

  it("searches and filters without hiding the other period permanently", () => {
    render(<ComposerDirectory composers={composers} />);

    fireEvent.change(screen.getByLabelText("작곡가 이름 검색"), {
      target: { value: "Debussy" },
    });
    expect(screen.getByText("1명의 작곡가")).toBeTruthy();
    expect(screen.queryByText("안토니오 비발디")).toBeNull();

    fireEvent.change(screen.getByLabelText("작곡가 이름 검색"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "바로크" }));
    expect(screen.getByText("2명의 작곡가")).toBeTruthy();
    expect(screen.queryByText("클로드 드뷔시")).toBeNull();
  });

  it("leads a period with portrait links without explicit importance labels", () => {
    render(<ComposerDirectory composers={composers} />);

    expect(screen.queryByText("핵심")).toBeNull();

    const baroqueSection = screen
      .getByRole("heading", { name: "바로크" })
      .closest("section");
    expect(baroqueSection).not.toBeNull();

    const featuredList = within(baroqueSection!).getByRole("list", {
      name: "바로크 먼저 만나는 작곡가",
    });
    const completeList = within(baroqueSection!).getByRole("list", {
      name: "바로크 전체 작곡가",
    });

    expect(featuredList.querySelectorAll("img")).toHaveLength(2);
    expect(featuredList.querySelector("img")?.getAttribute("alt")).toBe("");
    expect(
      within(featuredList)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual([
      composerHref("요한 제바스티안 바흐"),
      composerHref("안토니오 비발디"),
    ]);
    expect(
      within(completeList)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual([
      composerHref("안토니오 비발디"),
      composerHref("요한 제바스티안 바흐"),
    ]);
    expect(
      within(featuredList)
        .getByRole("link", { name: /요한 제바스티안 바흐/ })
        .getAttribute("href"),
    ).toBe(`/?composer=${encodeURIComponent("요한 제바스티안 바흐")}`);
  });

  it("keeps period headings and sorts original names within a period in A–Z mode", () => {
    render(
      <ComposerDirectory
        composers={[
          toComposerDirectoryEntry({
            id: "handel",
            name: "George Frideric Handel",
            nameKo: "게오르크 프리드리히 헨델",
            period: "Baroque",
          }),
          toComposerDirectoryEntry({
            id: "vivaldi",
            name: "Antonio Vivaldi",
            nameKo: "안토니오 비발디",
            period: "Baroque",
          }),
          toComposerDirectoryEntry({
            id: "adams",
            name: "John Adams",
            nameKo: "존 애덤스",
            period: "Unclassified",
          }),
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "A–Z" }));

    const baroqueHeading = screen.getByRole("heading", { name: "바로크" });
    const otherHeading = screen.getByRole("heading", { name: "기타" });
    const baroqueSection = baroqueHeading.closest("section");
    const completeBaroqueList = within(baroqueSection!).getByRole("list", {
      name: "바로크 전체 작곡가",
    });

    expect(baroqueSection).not.toBeNull();
    expect(
      within(completeBaroqueList)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual([
      composerHref("안토니오 비발디"),
      composerHref("게오르크 프리드리히 헨델"),
    ]);
    expect(otherHeading).toBeTruthy();
    const completeOtherList = within(otherHeading.closest("section")!).getByRole(
      "list",
      { name: "기타 전체 작곡가" },
    );
    expect(
      within(completeOtherList)
        .getByRole("link", { name: /존 애덤스/ })
        .getAttribute("href"),
    ).toBe(composerHref("존 애덤스"));
  });

  it("exposes period controls as a named group and updates pressed state", () => {
    render(<ComposerDirectory composers={composers} />);

    const periodControls = screen.getByRole("group", { name: "시대" });
    const allButton = within(periodControls).getByRole("button", { name: "전체" });
    const baroqueButton = within(periodControls).getByRole("button", {
      name: "바로크",
    });

    expect(allButton.getAttribute("aria-pressed")).toBe("true");
    expect(baroqueButton.getAttribute("aria-pressed")).toBe("false");

    fireEvent.click(baroqueButton);

    expect(allButton.getAttribute("aria-pressed")).toBe("false");
    expect(baroqueButton.getAttribute("aria-pressed")).toBe("true");
  });

  it("shows an explicit no-results state", () => {
    render(<ComposerDirectory composers={composers} />);

    fireEvent.change(screen.getByLabelText("작곡가 이름 검색"), {
      target: { value: "없는 작곡가" },
    });
    expect(screen.getByText("조건에 맞는 작곡가가 없습니다")).toBeTruthy();
  });

  it("hides portrait links during search to avoid duplicate results", () => {
    render(<ComposerDirectory composers={composers} />);

    fireEvent.change(screen.getByLabelText("작곡가 이름 검색"), {
      target: { value: "바흐" },
    });

    expect(
      screen.queryByRole("list", { name: "바로크 먼저 만나는 작곡가" }),
    ).toBeNull();
    expect(
      screen.getAllByRole("link", { name: /요한 제바스티안 바흐/ }),
    ).toHaveLength(1);
  });

  it("distinguishes a catalog load failure from a filtered empty list", () => {
    render(<ComposerDirectory composers={[]} />);

    expect(screen.getByText("작곡가 데이터를 불러오지 못했습니다")).toBeTruthy();
    expect(screen.getByRole("link", { name: "다시 시도" }).getAttribute("href")).toBe(
      "/composers",
    );
  });

  it("does not duplicate an original name when no Korean label exists", () => {
    render(
      <ComposerDirectory
        composers={[
          toComposerDirectoryEntry({
            id: "ades",
            name: "Thomas Adès",
            nameKo: null,
            period: "21st Century",
          }),
        ]}
      />,
    );

    expect(screen.getAllByText("Thomas Adès")).toHaveLength(1);
  });
});
