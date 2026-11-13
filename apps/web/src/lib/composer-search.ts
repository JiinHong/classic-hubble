import snapshot from "@/data/composer-index.json";
import { composerIdentityKey, toComposerDirectoryEntry } from "./composer-directory";

const fold = (s: string) => composerIdentityKey(s).normalize("NFC").replace(/\s+/g, " ");
const family = (s: string) => s.replace(/\s+(jr\.?|sr\.?|[12]세)$/i, "").split(" ").at(-1)!;
const rows = snapshot.filter(([, name]) => name !== "Traditional").map(([id, name, nameKo, period]) => {
  const person = toComposerDirectoryEntry({ id: id!, name: name!, nameKo, period });
  const names = [...new Set([fold(person.nameKo), fold(person.name)])];
  return { person, names, family: family(fold(person.name)) };
});
// Share translations of a surname even with relatives missing a Korean label.
const surnames = new Map<string, Set<string>>();
for (const row of rows) {
  const aliases = surnames.get(row.family) ?? new Set([row.family]);
  for (const name of row.names) if (name.includes(" ") && /[가-힣]/.test(name)) aliases.add(family(name));
  surnames.set(row.family, aliases);
}

export function matchComposers(raw: string) {
  const q = fold(raw);
  if (!q || q.length > 100) return { matches: [], exact: null };
  const hits = [];
  for (const row of rows) {
    const aliases = surnames.get(row.family)!;
    const rank = row.names.includes(q) ? 0 : aliases.has(q) ? 1
      : row.names.some(n => n.startsWith(q) || n.includes(" " + q)) || [...aliases].some(a => a.startsWith(q)) ? 2 : 3;
    if (rank < 3) hits.push({ person: row.person, rank });
  }
  hits.sort((a, b) => a.rank - b.rank ||
    (a.person.featuredRank ?? 99) - (b.person.featuredRank ?? 99) || a.person.name.localeCompare(b.person.name));
  const exact = hits.filter(h => h.rank <= 1);
  return { matches: hits.slice(0, 3).map(h => h.person), exact: exact.length === 1 ? exact[0].person : null };
}
