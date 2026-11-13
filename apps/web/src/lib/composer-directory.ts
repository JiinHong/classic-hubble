import koreanComposerNames from "@/data/composer-korean-names.json";
import portraitFiles from "@/data/composer-portrait-files.json";

export const PERIOD_OPTIONS = [
  { key: "all", label: "전체" },
  { key: "medieval", label: "중세" },
  { key: "renaissance", label: "르네상스" },
  { key: "baroque", label: "바로크" },
  { key: "classical", label: "고전" },
  { key: "romantic", label: "낭만" },
  { key: "twentieth", label: "20세기" },
  { key: "contemporary", label: "현대" },
] as const;

export type ComposerPeriodKey =
  | "medieval"
  | "renaissance"
  | "baroque"
  | "classical"
  | "romantic"
  | "twentieth"
  | "contemporary"
  | "other";

export type ComposerDirectorySort = "ko" | "latin";

export type ComposerDirectoryEntry = {
  featuredRank: number | null;
  id: string;
  name: string;
  nameKo: string;
  period: ComposerPeriodKey;
  portraitSrc: string | null;
};

type RawComposer = {
  id: string;
  name: string;
  nameKo: string | null;
  period: string | null;
};

type DirectoryOptions = {
  period: "all" | ComposerPeriodKey;
  query: string;
  sort: ComposerDirectorySort;
};

const PERIOD_ORDER: ComposerPeriodKey[] = [
  "medieval",
  "renaissance",
  "baroque",
  "classical",
  "romantic",
  "twentieth",
  "contemporary",
  "other",
];

export const PERIOD_LABELS: Record<ComposerPeriodKey, string> = {
  baroque: "바로크",
  classical: "고전",
  contemporary: "현대",
  medieval: "중세",
  other: "기타",
  renaissance: "르네상스",
  romantic: "낭만",
  twentieth: "20세기",
};

const featuredRanks = new Map<string, number>(([
  ["Guillaume de Machaut", 1],
  ["Guillaume Dufay", 2],
  ["Léonin", 3],
  ["Pérotin", 4],
  ["Claudio Monteverdi", 1],
  ["Giovanni Pierluigi da Palestrina", 2],
  ["Josquin Des Prez", 3],
  ["William Byrd", 4],
  ["Johann Sebastian Bach", 1],
  ["George Frideric Handel", 2],
  ["Antonio Vivaldi", 3],
  ["Henry Purcell", 4],
  ["Wolfgang Amadeus Mozart", 1],
  ["Franz Joseph Haydn", 2],
  ["Christoph Willibald von Gluck", 3],
  ["Luigi Boccherini", 4],
  ["Ludwig van Beethoven", 1],
  ["Frédéric Chopin", 2],
  ["Pyotr Ilyich Tchaikovsky", 3],
  ["Johannes Brahms", 4],
  ["Franz Schubert", 5],
  ["Igor Stravinsky", 1],
  ["Dmitri Shostakovich", 2],
  ["Sergei Prokofiev", 3],
  ["Béla Bartók", 4],
  ["Arvo Pärt", 1],
  ["Philip Glass", 2],
  ["Steve Reich", 3],
  ["John Adams", 4],
] as const).map(([name, rank]) => [normalizeText(name), rank]));

const KOREAN_COMPOSER_LABELS = new Map(
  Object.entries(koreanComposerNames).map(([name, nameKo]) => [
    normalizeText(name),
    nameKo,
  ]),
);

const portraits = new Map(Object.entries(portraitFiles).map(([name, file]) =>
  [normalizeText(name), "/composer-portraits/" + file]));

export function koreanComposerLabel(identityKey: string) {
  return KOREAN_COMPOSER_LABELS.get(identityKey);
}

function normalizeText(value: string) {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase()
    .trim();
}

function normalizePeriod(value: string | null): ComposerPeriodKey {
  const period = normalizeText(value ?? "");
  if (period.includes("medieval") || period.includes("중세")) return "medieval";
  if (period.includes("renaissance") || period.includes("르네상스")) {
    return "renaissance";
  }
  if (period.includes("baroque") || period.includes("바로크")) return "baroque";
  if (period.includes("classical") || period.includes("고전")) return "classical";
  if (period.includes("romantic") || period.includes("낭만")) return "romantic";
  if (
    period.includes("20th") ||
    period.includes("modern") ||
    period.includes("20세기") ||
    period.includes("근현대")
  ) {
    return "twentieth";
  }
  if (
    period.includes("contemporary") ||
    period.includes("post-war") ||
    period.includes("21st century") ||
    period.includes("현대")
  ) {
    return "contemporary";
  }
  return "other";
}

export function toComposerDirectoryEntry(input: RawComposer): ComposerDirectoryEntry {
  const identityKey = normalizeText(input.name);

  return {
    featuredRank: featuredRanks.get(identityKey) ?? null,
    id: input.id,
    name: input.name.trim(),
    nameKo:
      input.nameKo?.trim() ||
      koreanComposerLabel(identityKey) ||
      input.name.trim(),
    period: normalizePeriod(input.period),
    portraitSrc: portraits.get(identityKey) ?? null,
  };
}

export function filterAndSortComposers(
  entries: ComposerDirectoryEntry[],
  options: DirectoryOptions,
) {
  const query = normalizeText(options.query);
  const locale = options.sort === "ko" ? "ko-KR" : "en";
  const collator = new Intl.Collator(locale, { sensitivity: "base" });

  return entries
    .filter((entry) => options.period === "all" || entry.period === options.period)
    .filter((entry) => {
      if (!query) return true;
      return normalizeText(`${entry.nameKo} ${entry.name}`).includes(query);
    })
    .toSorted((a, b) =>
      collator.compare(
        options.sort === "ko" ? a.nameKo : a.name,
        options.sort === "ko" ? b.nameKo : b.name,
      ),
    );
}

export function groupComposers(entries: ComposerDirectoryEntry[]) {
  return PERIOD_ORDER.map((key) => ({
    composers: entries.filter((entry) => entry.period === key),
    key,
    label: PERIOD_LABELS[key],
  })).filter((group) => group.composers.length > 0);
}

export function selectFeaturedComposers(entries: ComposerDirectoryEntry[]) {
  return entries
    .filter(
      (entry) => entry.featuredRank !== null && entry.portraitSrc !== null,
    )
    .toSorted(
      (a, b) =>
        (a.featuredRank ?? Number.MAX_SAFE_INTEGER) -
          (b.featuredRank ?? Number.MAX_SAFE_INTEGER) ||
        a.name.localeCompare(b.name, "en"),
    )
    .slice(0, 4);
}

export function composerDiscoveryHref(
  composer: Pick<ComposerDirectoryEntry, "id">,
) {
  return `/composers/${encodeURIComponent(composer.id)}`;
}

export function composerIdentityKey(name: string) {
  return normalizeText(name);
}
