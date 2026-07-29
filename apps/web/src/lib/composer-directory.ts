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
      [
        "Guillaume de Machaut",
        "기욤 드 마쇼",
        1,
        "guillaume-de-machaut",
      ],
      ["Guillaume Dufay", "기욤 뒤파이", 2, "guillaume-dufay"],
      ["Léonin", "레오냉", 3, "leonin"],
      ["Pérotin", "페로탱", 4, "perotin"],
      [
        "Claudio Monteverdi",
        "클라우디오 몬테베르디",
        1,
        "claudio-monteverdi",
      ],
      [
        "Giovanni Pierluigi da Palestrina",
        "조반니 피에를루이지 다 팔레스트리나",
        2,
        "giovanni-pierluigi-da-palestrina",
      ],
      ["Josquin Des Prez", "조스캥 데프레", 3, "josquin-des-prez"],
      ["William Byrd", "윌리엄 버드", 4, "william-byrd"],
      [
        "Johann Sebastian Bach",
        "요한 제바스티안 바흐",
        1,
        "johann-sebastian-bach",
      ],
      [
        "George Frideric Handel",
        "게오르크 프리드리히 헨델",
        2,
        "george-frideric-handel",
      ],
      ["Antonio Vivaldi", "안토니오 비발디", 3, "antonio-vivaldi"],
      ["Henry Purcell", "헨리 퍼셀", 4, "henry-purcell"],
      [
        "Wolfgang Amadeus Mozart",
        "볼프강 아마데우스 모차르트",
        1,
        "wolfgang-amadeus-mozart",
      ],
      ["Franz Joseph Haydn", "요제프 하이든", 2, "franz-joseph-haydn"],
      [
        "Christoph Willibald von Gluck",
        "크리스토프 빌리발트 글루크",
        3,
        "christoph-willibald-von-gluck",
      ],
      ["Luigi Boccherini", "루이지 보케리니", 4, "luigi-boccherini"],
      [
        "Ludwig van Beethoven",
        "루트비히 판 베토벤",
        1,
        "ludwig-van-beethoven",
      ],
      ["Frédéric Chopin", "프레데리크 쇼팽", 2, "frederic-chopin"],
      [
        "Pyotr Ilyich Tchaikovsky",
        "표트르 일리치 차이콥스키",
        3,
        "pyotr-ilyich-tchaikovsky",
      ],
      ["Johannes Brahms", "요하네스 브람스", 4, "johannes-brahms"],
      ["Igor Stravinsky", "이고르 스트라빈스키", 1, "igor-stravinsky"],
      [
        "Dmitri Shostakovich",
        "드미트리 쇼스타코비치",
        2,
        "dmitri-shostakovich",
      ],
      ["Sergei Prokofiev", "세르게이 프로코피예프", 3, "sergei-prokofiev"],
      ["Béla Bartók", "벨라 바르톡", 4, "bela-bartok"],
      ["Arvo Pärt", "아르보 패르트", 1, "arvo-part"],
      ["Philip Glass", "필립 글래스", 2, "philip-glass"],
      ["Steve Reich", "스티브 라이히", 3, "steve-reich"],
      ["John Adams", "존 애덤스", 4, "john-adams"],
    ] as const
  ).map(([name, nameKo, featuredRank, portraitSlug]) => [
    normalizeText(name),
    {
      featuredRank,
      nameKo,
      portraitSrc: `/composer-portraits/${portraitSlug}.jpg`,
    },
  ]),
);

const ADDITIONAL_KOREAN_COMPOSER_LABELS = new Map(
  (
    [
      ["Franz Schubert", "프란츠 슈베르트"],
      ["Robert Schumann", "로베르트 슈만"],
      ["Franz Liszt", "프란츠 리스트"],
      ["Richard Wagner", "리하르트 바그너"],
      ["Antonín Dvořák", "안토닌 드보르자크"],
      ["Gustav Mahler", "구스타프 말러"],
      ["Claude Debussy", "클로드 드뷔시"],
      ["Maurice Ravel", "모리스 라벨"],
      ["Sergei Rachmaninoff", "세르게이 라흐마니노프"],
    ] as const
  ).map(([name, nameKo]) => [normalizeText(name), nameKo]),
);

function koreanComposerLabel(identityKey: string) {
  return (
    FEATURED_COMPOSER_METADATA.get(identityKey)?.nameKo ??
    ADDITIONAL_KOREAN_COMPOSER_LABELS.get(identityKey)
  );
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
