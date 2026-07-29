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
  id: string;
  isCore: boolean;
  name: string;
  nameKo: string;
  period: ComposerPeriodKey;
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

const CORE_COMPOSER_LABELS = new Map(
  (
    [
      ["Antonio Vivaldi", "안토니오 비발디"],
      ["Johann Sebastian Bach", "요한 제바스티안 바흐"],
      ["George Frideric Handel", "게오르크 프리드리히 헨델"],
      ["Franz Joseph Haydn", "요제프 하이든"],
      ["Wolfgang Amadeus Mozart", "볼프강 아마데우스 모차르트"],
      ["Ludwig van Beethoven", "루트비히 판 베토벤"],
      ["Franz Schubert", "프란츠 슈베르트"],
      ["Robert Schumann", "로베르트 슈만"],
      ["Frédéric Chopin", "프레데리크 쇼팽"],
      ["Franz Liszt", "프란츠 리스트"],
      ["Richard Wagner", "리하르트 바그너"],
      ["Johannes Brahms", "요하네스 브람스"],
      ["Pyotr Ilyich Tchaikovsky", "표트르 일리치 차이콥스키"],
      ["Antonín Dvořák", "안토닌 드보르자크"],
      ["Gustav Mahler", "구스타프 말러"],
      ["Claude Debussy", "클로드 드뷔시"],
      ["Maurice Ravel", "모리스 라벨"],
      ["Sergei Rachmaninoff", "세르게이 라흐마니노프"],
      ["Igor Stravinsky", "이고르 스트라빈스키"],
      ["Dmitri Shostakovich", "드미트리 쇼스타코비치"],
    ] as const
  ).map(([name, nameKo]) => [normalizeText(name), nameKo]),
);

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
    id: input.id,
    isCore: CORE_COMPOSER_LABELS.has(identityKey),
    name: input.name.trim(),
    nameKo:
      input.nameKo?.trim() ||
      CORE_COMPOSER_LABELS.get(identityKey) ||
      input.name.trim(),
    period: normalizePeriod(input.period),
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

export function composerDiscoveryHref(
  composer: Pick<ComposerDirectoryEntry, "name" | "nameKo">,
) {
  return `/?composer=${encodeURIComponent(composer.nameKo || composer.name)}`;
}

export function composerIdentityKey(name: string) {
  return normalizeText(name);
}
