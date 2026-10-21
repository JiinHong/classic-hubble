import { render } from "@testing-library/react";
import { expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ catalog: vi.fn(), view: vi.fn(() => null) }));
vi.mock("@/lib/catalog", () => ({ getCatalogSnapshot: mocks.catalog }));
vi.mock("@/components/WatchlistExperience", () => ({
  WatchlistExperience: mocks.view,
}));
import Page from "./page";
it("opens the private library shell without sending the public catalog", async () => {
  mocks.catalog.mockResolvedValue({ works: [], performances: [] });
  render(await Page());
  expect(mocks.catalog).not.toHaveBeenCalled();
  expect(mocks.view).toHaveBeenCalledWith({}, undefined);
});
