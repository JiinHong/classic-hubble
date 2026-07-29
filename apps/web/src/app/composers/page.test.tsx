import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  ComposerDirectory: vi.fn(() => null),
  getComposerDirectory: vi.fn(),
}));

vi.mock("@/components/ComposerDirectory", () => ({
  ComposerDirectory: mocks.ComposerDirectory,
}));

vi.mock("@/lib/catalog", () => ({
  getComposerDirectory: mocks.getComposerDirectory,
}));

import * as composersPage from "./page";

afterEach(() => {
  mocks.ComposerDirectory.mockClear();
  mocks.getComposerDirectory.mockReset();
});

describe("ComposersPage", () => {
  it("loads curated composer data at request time", () => {
    expect((composersPage as { dynamic?: string }).dynamic).toBe(
      "force-dynamic",
    );
  });

  it("passes the composer loader result to the directory", async () => {
    const composers = [
      {
        id: "bach",
        isCore: true,
        name: "Johann Sebastian Bach",
        nameKo: "요한 제바스티안 바흐",
        period: "baroque" as const,
      },
    ];
    mocks.getComposerDirectory.mockResolvedValue(composers);

    render(await composersPage.default());

    expect(mocks.getComposerDirectory).toHaveBeenCalledOnce();
    expect(mocks.ComposerDirectory).toHaveBeenCalledWith(
      { composers },
      undefined,
    );
  });
});
