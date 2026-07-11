import { WatchlistExperience } from "@/components/WatchlistExperience";
import { getCatalogSnapshot } from "@/lib/catalog";

export default async function WatchlistPage() {
  const catalog = await getCatalogSnapshot();

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <WatchlistExperience
        performances={catalog.performances}
        works={catalog.works}
      />
    </main>
  );
}
