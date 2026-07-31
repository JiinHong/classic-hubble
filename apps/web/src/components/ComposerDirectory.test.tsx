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
    id: "scarlatti",
    name: "Domenico Scarlatti",
    nameKo: "도메니코 스카를라티",
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

    expect(screen.getByText("4명의 작곡가")).toBeTruthy();
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
    expect(screen.getByText("3명의 작곡가")).toBeTruthy();
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
    const plainList = within(baroqueSection!).getByRole("list", {
      name: "바로크 작곡가 목록",
    });

    const featuredImages = featuredList.querySelectorAll("img");
    expect(featuredImages).toHaveLength(2);
    expect(featuredImages[0]?.getAttribute("alt")).toBe("");
    expect(featuredImages[0]?.getAttribute("loading")).toBe("eager");
    expect(featuredImages[1]?.getAttribute("loading")).toBe("lazy");
    expect(
      within(featuredList)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual([
      composerHref("요한 제바스티안 바흐"),
      composerHref("안토니오 비발디"),
    ]);
    expect(
      within(plainList)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual([composerHref("도메니코 스카를라티")]);
    expect(
      within(baroqueSection!).getAllByRole("link", {
        name: /요한 제바스티안 바흐/,
      }),
    ).toHaveLength(1);
    const plainLink = within(plainList).getByRole("link", {
      name: /도메니코 스카를라티.*Domenico Scarlatti/,
    });
    expect(plainLink.children[0]?.textContent).toBe("도메니코 스카를라티");
    expect(plainLink.children[1]?.textContent).toBe("Domenico Scarlatti");
    expect(
      within(featuredList)
        .getByRole("link", { name: /요한 제바스티안 바흐/ })
        .getAttribute("href"),
    ).toBe(`/?composer=${encodeURIComponent("요한 제바스티안 바흐")}`);
  });

  it("omits a plain list when a period contains only featured composers", () => {
    render(
      <ComposerDirectory
        composers={[
          toComposerDirectoryEntry({
            id: "bach",
            name: "Johann Sebastian Bach",
            nameKo: "요한 제바스티안 바흐",
            period: "Baroque",
          }),
        ]}
      />,
    );

    const baroqueSection = screen
      .getByRole("heading", { name: "바로크" })
      .closest("section");
    expect(baroqueSection).not.toBeNull();
    expect(
      within(baroqueSection!).queryByRole("list", {
        name: "바로크 작곡가 목록",
      }),
    ).toBeNull();
    expect(within(baroqueSection!).getAllByRole("list")).toHaveLength(1);
  });

  it("keeps period headings and sorts original names within a period in A–Z mode", () => {
    render(
      <ComposerDirectory
        composers={[
          toComposerDirectoryEntry({
            id: "scarlatti",
            name: "Domenico Scarlatti",
            nameKo: "도메니코 스카를라티",
            period: "Baroque",
          }),
          toComposerDirectoryEntry({
            id: "rameau",
            name: "Jean-Philippe Rameau",
            nameKo: "장필리프 라모",
            period: "Baroque",
          }),
          toComposerDirectoryEntry({
            id: "test-composer",
            name: "Test Composer",
            nameKo: "테스트 작곡가",
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
      name: "바로크 작곡가 목록",
    });

    expect(baroqueSection).not.toBeNull();
    expect(
      within(completeBaroqueList)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual([
      composerHref("도메니코 스카를라티"),
      composerHref("장필리프 라모"),
    ]);
    expect(otherHeading).toBeTruthy();
    const completeOtherList = within(otherHeading.closest("section")!).getByRole(
      "list",
      { name: "기타 작곡가 목록" },
    );
    expect(
      within(completeOtherList)
        .getByRole("link", { name: /테스트 작곡가/ })
        .getAttribute("href"),
    ).toBe(composerHref("테스트 작곡가"));
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
