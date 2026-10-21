import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
const getCatalogSnapshot = vi.hoisted(() => vi.fn());
vi.mock("@/lib/catalog", () => ({ getCatalogSnapshot }));
import Page from "./page";
it("opens the search form without loading the catalog", async () => {
  getCatalogSnapshot.mockResolvedValue({ works: [], source: "supabase" });
  render(await Page());
  expect(screen.getByLabelText("유튜브 영상 링크")).toBeTruthy();
  expect(getCatalogSnapshot).not.toHaveBeenCalled();
});
