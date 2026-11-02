import { SearchExperience } from "@/components/SearchExperience";

type HomeProps = { searchParams: Promise<Record<string, string | string[] | undefined>> };
const first = (value: string | string[] | undefined) => (Array.isArray(value) ? value[0] : value) ?? "";

export default async function Home({ searchParams }: HomeProps) {
  const params = await searchParams;
  const initialQuery = first(params.q ?? params.composer).slice(0, 200).trim();
  const candidate = first(params.work);
  const initialWork = /^[a-z0-9-]{1,160}$/.test(candidate) ? candidate : "";
  const initialMode = first(params.mode) === "performances" ? "performances" : "works";
  const initialCity = first(params.city).slice(0, 80) || "전체";
  return <main><SearchExperience key={JSON.stringify([initialQuery, initialWork, initialMode, initialCity])}
    initialQuery={initialQuery} initialWork={initialWork} initialMode={initialMode} initialCity={initialCity} /></main>;
}
