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

function composerLinkHrefs() {
  return screen
    .getAllByRole("link")
    .map((link) => link.getAttribute("href"));
}

describe("ComposerDirectory", () => {
  it("shows all composers with Korean and original names", () => {
    render(<ComposerDirectory composers={composers} />);

    expect(screen.getByText("3명의 작곡가")).toBeTruthy();
    expect(screen.getByText("요한 제바스티안 바흐")).toBeTruthy();
    expect(screen.getByText("Johann Sebastian Bach")).toBeTruthy();
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

  it("marks core composers and links them to discovery", () => {
    render(<ComposerDirectory composers={composers} />);

    expect(screen.getAllByText("핵심").length).toBeGreaterThan(0);
    expect(
      screen
        .getByRole("link", { name: /요한 제바스티안 바흐/ })
        .getAttribute("href"),
    ).toBe(`/?composer=${encodeURIComponent("요한 제바스티안 바흐")}`);
  });

  it("shows complete Korean and original-language composer link orders", () => {
    render(<ComposerDirectory composers={composers} />);

    expect(composerLinkHrefs()).toEqual([
      composerHref("안토니오 비발디"),
      composerHref("요한 제바스티안 바흐"),
      composerHref("클로드 드뷔시"),
    ]);

    fireEvent.click(screen.getByRole("button", { name: "A–Z" }));
    expect(composerLinkHrefs()).toEqual([
      composerHref("안토니오 비발디"),
      composerHref("클로드 드뷔시"),
      composerHref("요한 제바스티안 바흐"),
    ]);
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
            id: "adams",
            name: "John Adams",
            nameKo: null,
            period: "21st Century",
          }),
        ]}
      />,
    );

    expect(screen.getAllByText("John Adams")).toHaveLength(1);
  });
});
