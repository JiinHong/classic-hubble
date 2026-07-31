import koreanComposerNames from "@/data/composer-korean-names.json";

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

const PERIOD_LABELS: Record<ComposerPeriodKey, string> = {
  baroque: "바로크",
  classical: "고전",
  contemporary: "현대",
  medieval: "중세",
  other: "기타",
  renaissance: "르네상스",
  romantic: "낭만",
  twentieth: "20세기",
};

const FEATURED_COMPOSER_METADATA = new Map(
  (
    [
      ["Guillaume de Machaut", 1, "guillaume-de-machaut"],
      ["Guillaume Dufay", 2, "guillaume-dufay"],
      ["Léonin", 3, "leonin"],
      ["Pérotin", 4, "perotin"],
      ["Claudio Monteverdi", 1, "claudio-monteverdi"],
      [
        "Giovanni Pierluigi da Palestrina",
        2,
        "giovanni-pierluigi-da-palestrina",
      ],
      ["Josquin Des Prez", 3, "josquin-des-prez"],
      ["William Byrd", 4, "william-byrd"],
      ["Johann Sebastian Bach", 1, "johann-sebastian-bach"],
      [
        "George Frideric Handel",
        2,
        "george-frideric-handel",
      ],
      ["Antonio Vivaldi", 3, "antonio-vivaldi"],
      ["Henry Purcell", 4, "henry-purcell"],
      [
        "Wolfgang Amadeus Mozart",
        1,
        "wolfgang-amadeus-mozart",
      ],
      ["Franz Joseph Haydn", 2, "franz-joseph-haydn"],
      [
        "Christoph Willibald von Gluck",
        3,
        "christoph-willibald-von-gluck",
      ],
      ["Luigi Boccherini", 4, "luigi-boccherini"],
      [
        "Ludwig van Beethoven",
        1,
        "ludwig-van-beethoven",
      ],
      ["Frédéric Chopin", 2, "frederic-chopin"],
      [
        "Pyotr Ilyich Tchaikovsky",
        3,
        "pyotr-ilyich-tchaikovsky",
      ],
      ["Johannes Brahms", 4, "johannes-brahms"],
      ["Franz Schubert", 5, "franz-schubert"],
      ["Igor Stravinsky", 1, "igor-stravinsky"],
      [
        "Dmitri Shostakovich",
        2,
        "dmitri-shostakovich",
      ],
      ["Sergei Prokofiev", 3, "sergei-prokofiev"],
      ["Béla Bartók", 4, "bela-bartok"],
      ["Arvo Pärt", 1, "arvo-part"],
      ["Philip Glass", 2, "philip-glass"],
      ["Steve Reich", 3, "steve-reich"],
      ["John Adams", 4, "john-adams"],
    ] as const
  ).map(([name, featuredRank, portraitSlug]) => [
    normalizeText(name),
    {
      featuredRank,
      portraitSrc: `/composer-portraits/${portraitSlug}.jpg`,
    },
  ]),
);

const KOREAN_COMPOSER_LABELS = new Map(
  Object.entries(koreanComposerNames).map(([name, nameKo]) => [
    normalizeText(name),
    nameKo,
  ]),
);

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
  const featuredMetadata = FEATURED_COMPOSER_METADATA.get(identityKey);

  return {
    featuredRank: featuredMetadata?.featuredRank ?? null,
    id: input.id,
    name: input.name.trim(),
    nameKo:
      input.nameKo?.trim() ||
      koreanComposerLabel(identityKey) ||
      input.name.trim(),
    period: normalizePeriod(input.period),
    portraitSrc: featuredMetadata?.portraitSrc ?? null,
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
  composer: Pick<ComposerDirectoryEntry, "name" | "nameKo">,
) {
  return `/?composer=${encodeURIComponent(composer.nameKo || composer.name)}`;
}

export function composerIdentityKey(name: string) {
  return normalizeText(name);
}
