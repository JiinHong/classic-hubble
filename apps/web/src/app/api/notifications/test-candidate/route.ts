import { getUpcomingPerformancesFromList } from "@classic-hubble/shared";
import { NextResponse } from "next/server";

import { getCatalogSnapshot } from "@/lib/catalog";

export async function GET() {
  const catalog = await getCatalogSnapshot();
  const performance = getUpcomingPerformancesFromList(catalog.performances)[0];

  return NextResponse.json({
    ok: true,
    candidate: performance
      ? {
          title: performance.title,
          venue: performance.venue,
          date: performance.date,
          program: performance.program.map((item) => item.displayTitle),
        }
      : null,
  });
}
