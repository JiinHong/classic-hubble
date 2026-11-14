import { normalizeWorkSearchText } from "@classic-hubble/shared";

// For ambiguous, unqualified titles only. Never use this to identify concert repertoire.
const preferredByTitle = new Map([
  ["달빛", "wikidata-q29117946"],
  ["clair de lune", "wikidata-q29117946"],
]);

export function orderForWorkDiscovery<T extends { slug: string }>(works: T[], query: string): T[] {
  const preferred = preferredByTitle.get(normalizeWorkSearchText(query));
  if (!preferred) return works;
  const index = works.findIndex(work => work.slug === preferred);
  if (index <= 0) return works;
  return [works[index], ...works.slice(0, index), ...works.slice(index + 1)];
}
