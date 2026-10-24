export type ConfidenceLevel =
  | "official"
  | "verified"
  | "ocr"
  | "estimated"
  | "unknown";

export type ProgramPublicationStatus =
  | "unknown"
  | "confirmed"
  | "partially_confirmed"
  | "image_only"
  | "not_published"
  | "selected_on_day"
  | "announced_later";

export type Composer = {
  id: string;
  name: string;
  nameKo: string;
  period: string;
};

export type WorkReference = {
  slug: string;
  title: string;
  titleKo: string;
  catalogue: string;
  position: number | null;
  aliases?: string[];
};

export type Work = {
  slug: string;
  title: string;
  titleKo: string;
  composer: Composer;
  catalogue: string;
  aliases: string[];
  instrumentation: string;
  popularityRank: number | null;
  referenceUrl?: string;
  partOf?: WorkReference[];
  parts?: WorkReference[];
  upcomingPerformanceIds: string[];
};

export type ProgramSource = {
  type: ConfidenceLevel;
  label: string;
  confidence: number | null;
};

export type ProgramItem = {
  workSlug: string;
  displayTitle: string;
  composerName: string;
  source: ProgramSource;
};

export type Performance = {
  id: string;
  title: string;
  venue: string;
  city: string;
  date: string;
  time: string;
  priceRange: string;
  artists: string[];
  bookingUrl: string;
  posterUrl: string;
  status: "open" | "upcoming" | "soldout" | "closed";
  endDate?: string;
  sourceLabel: string;
  program: ProgramItem[];
  programStatus?: ProgramPublicationStatus;
  programSourceUrl?: string | null;
  programImageUrls?: string[];
};

export type ReviewItem = {
  id: string;
  performanceId: string;
  imageUrl: string;
  extractedText: string;
  suggestedWorkSlug: string | null;
  confidence: number;
  state: "needs_review" | "approved" | "rejected";
};

const composers: Record<string, Composer> = {
  beethoven: {
    id: "beethoven",
    name: "Ludwig van Beethoven",
    nameKo: "루트비히 판 베토벤",
    period: "Classical / Romantic",
  },
  rachmaninoff: {
    id: "rachmaninoff",
    name: "Sergei Rachmaninoff",
    nameKo: "세르게이 라흐마니노프",
    period: "Late Romantic",
  },
  dvorak: {
    id: "dvorak",
    name: "Antonin Dvorak",
    nameKo: "안토닌 드보르자크",
    period: "Romantic",
  },
  brahms: {
    id: "brahms",
    name: "Johannes Brahms",
    nameKo: "요하네스 브람스",
    period: "Romantic",
  },
};

export const works: Work[] = [
  {
    slug: "rachmaninoff-piano-concerto-2",
    title: "Piano Concerto No. 2 in C minor",
    titleKo: "피아노 협주곡 2번",
    composer: composers.rachmaninoff,
    catalogue: "Op. 18",
    aliases: [
      "라흐마니노프 피아노 협주곡 2번",
      "라흐 피협 2번",
      "라피협 2",
      "Rachmaninoff Piano Concerto No. 2",
      "Piano Concerto No.2 Op.18",
    ],
    instrumentation: "Piano and Orchestra",
    popularityRank: 1,
    upcomingPerformanceIds: ["perf-lotte-rach-2", "perf-sac-gala"],
  },
  {
    slug: "beethoven-symphony-5",
    title: "Symphony No. 5 in C minor",
    titleKo: "교향곡 5번",
    composer: composers.beethoven,
    catalogue: "Op. 67",
    aliases: [
      "운명",
      "베토벤 교향곡 5번",
      "Beethoven Symphony No. 5",
      "Symphony No.5 in C minor",
      "Fate Symphony",
    ],
    instrumentation: "Orchestra",
    popularityRank: 2,
    upcomingPerformanceIds: ["perf-sejong-beethoven"],
  },
  {
    slug: "dvorak-symphony-9",
    title: "Symphony No. 9 in E minor",
    titleKo: "교향곡 9번 신세계로부터",
    composer: composers.dvorak,
    catalogue: "Op. 95",
    aliases: [
      "신세계",
      "드보르자크 신세계",
      "드보르자크 교향곡 9번",
      "From the New World",
      "Dvorak Symphony No. 9",
    ],
    instrumentation: "Orchestra",
    popularityRank: 3,
    upcomingPerformanceIds: ["perf-bucheon-dvorak"],
  },
  {
    slug: "brahms-violin-concerto",
    title: "Violin Concerto in D major",
    titleKo: "바이올린 협주곡",
    composer: composers.brahms,
    catalogue: "Op. 77",
    aliases: [
      "브람스 바이올린 협주곡",
      "브바협",
      "Brahms Violin Concerto",
      "Violin Concerto Op.77",
    ],
    instrumentation: "Violin and Orchestra",
    popularityRank: 4,
    upcomingPerformanceIds: ["perf-incheon-brahms"],
  },
];

export const performances: Performance[] = [
  {
    id: "perf-lotte-rach-2",
    title: "김정원과 친구들 - 저먼 로맨틱스",
    venue: "롯데콘서트홀",
    city: "서울",
    date: "2026-07-31",
    time: "19:30",
    priceRange: "R 90,000 / S 70,000 / A 50,000",
    artists: ["김정원", "KBS교향악단"],
    bookingUrl: "https://tickets.interpark.com/",
    posterUrl:
      "https://ticketimage.interpark.com/Play/image/large/26/26009683_p.gif",
    status: "open",
    sourceLabel: "공연장 상세 이미지 OCR + 관리자 검수",
    program: [
      {
        workSlug: "rachmaninoff-piano-concerto-2",
        displayTitle: "Rachmaninoff Piano Concerto No. 2 in C minor, Op. 18",
        composerName: "Sergei Rachmaninoff",
        source: { type: "verified", label: "검수 완료", confidence: 0.93 },
      },
    ],
  },
  {
    id: "perf-sac-gala",
    title: "2026 서초국제예술단 피아노 갈라 콘서트",
    venue: "예술의전당 IBK챔버홀",
    city: "서울",
    date: "2026-08-29",
    time: "17:00",
    priceRange: "전석 40,000",
    artists: ["원재연", "김수연"],
    bookingUrl: "https://www.sac.or.kr/",
    posterUrl:
      "https://ticketimage.interpark.com/Play/image/large/26/26009095_p.gif",
    status: "upcoming",
    sourceLabel: "KOPIS + 예술의전당 상세페이지",
    program: [
      {
        workSlug: "rachmaninoff-piano-concerto-2",
        displayTitle: "라흐마니노프 피아노 협주곡 2번",
        composerName: "세르게이 라흐마니노프",
        source: { type: "ocr", label: "OCR 추출", confidence: 0.82 },
      },
    ],
  },
  {
    id: "perf-sejong-beethoven",
    title: "서울시향 베토벤 사이클",
    venue: "세종문화회관 세종대극장",
    city: "서울",
    date: "2026-09-12",
    time: "19:30",
    priceRange: "50,000 - 120,000",
    artists: ["서울시립교향악단", "수산나 멜키"],
    bookingUrl: "https://www.sejongpac.or.kr/",
    posterUrl:
      "https://ticketimage.interpark.com/Play/image/large/26/26006680_p.gif",
    status: "open",
    sourceLabel: "공식 프로그램 확인",
    program: [
      {
        workSlug: "beethoven-symphony-5",
        displayTitle: "베토벤 교향곡 5번 다단조 Op. 67",
        composerName: "루트비히 판 베토벤",
        source: { type: "official", label: "공식 확인", confidence: 0.99 },
      },
    ],
  },
  {
    id: "perf-bucheon-dvorak",
    title: "부천필하모닉 정기연주회 - ENIGMA",
    venue: "부천아트센터 콘서트홀",
    city: "부천",
    date: "2026-10-16",
    time: "19:30",
    priceRange: "30,000 - 70,000",
    artists: ["부천필하모닉오케스트라"],
    bookingUrl: "https://www.bac.or.kr/",
    posterUrl: "https://www.bac.or.kr/images/snsShareImage1.png",
    status: "open",
    sourceLabel: "부천아트센터 상세페이지",
    program: [
      {
        workSlug: "dvorak-symphony-9",
        displayTitle: "Dvorak Symphony No. 9 From the New World",
        composerName: "Antonin Dvorak",
        source: { type: "estimated", label: "추정 매칭", confidence: 0.74 },
      },
    ],
  },
  {
    id: "perf-incheon-brahms",
    title: "아트센터인천 마스터즈 시리즈",
    venue: "아트센터인천 콘서트홀",
    city: "인천",
    date: "2026-11-08",
    time: "17:00",
    priceRange: "40,000 - 110,000",
    artists: ["드레스덴 필하모닉", "제임스 에네스"],
    bookingUrl: "https://www.aci.or.kr/",
    posterUrl:
      "https://ticketimage.interpark.com/Play/image/large/26/26005009_p.gif",
    status: "open",
    sourceLabel: "NOL 예매 정보 + 공연장 페이지",
    program: [
      {
        workSlug: "brahms-violin-concerto",
        displayTitle: "Brahms Violin Concerto in D major, Op. 77",
        composerName: "Johannes Brahms",
        source: { type: "verified", label: "검수 완료", confidence: 0.91 },
      },
    ],
  },
];

export const reviewQueue: ReviewItem[] = [
  {
    id: "review-001",
    performanceId: "perf-sac-gala",
    imageUrl:
      "https://ticketimage.interpark.com/Play/image/large/26/26009095_p.gif",
    extractedText: "Rachmaninoff Piano Concerto No. 2 in C minor Op.18",
    suggestedWorkSlug: "rachmaninoff-piano-concerto-2",
    confidence: 0.82,
    state: "needs_review",
  },
  {
    id: "review-002",
    performanceId: "perf-bucheon-dvorak",
    imageUrl: "https://www.bac.or.kr/images/snsShareImage1.png",
    extractedText: "Dvorak Symphony No.9 New World",
    suggestedWorkSlug: "dvorak-symphony-9",
    confidence: 0.74,
    state: "needs_review",
  },
];

// Observed genre shorthand; this expands queries, not canonical work identities.
const genreShorthand: Record<string, string> = {
  피협: "피아노 협주곡",
  바협: "바이올린 협주곡",
  피소: "피아노 소나타",
  현사: "현악 사중주",
};

const normalize = (value: string) =>
  value
    .normalize("NFC")
    .toLowerCase()
    .replace(
      /(피협|바협|피소|현사)\s*(?:제\s*)?(\d+)(?:번)?(?=$|\s|[^가-힣\d])/g,
      (_, genre: string, number: string) => ` ${genreShorthand[genre]} ${number}번 `,
    )
    .replace(
      /(피협|바협|피소|현사)(?=\s|$)/g,
      (_, genre: string) => ` ${genreShorthand[genre]} `,
    )
    .replace(/현악\s*4중주/g, "현악 사중주")
    .replace(/(?:제\s*)?(\d+)\s*(?:번|곡)(?=$|\s|[^가-힣])/g, " $1번 ")
    .replace(/[.,:;'"“”‘’〈〉<>()\[\]\-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const tokenMatches = (candidate: string, token: string) => {
  if (/^\d+번$/.test(token)) return candidate.split(" ").includes(token);
  if (/^\d+$/.test(token)) return new RegExp(`(?:^|\\D)${token}(?!\\d)`).test(candidate);
  if (/^[가-힣]+$/.test(token)) return candidate.replace(/\s/g, "").includes(token);
  return candidate.includes(token);
};

const searchTermsCache = new WeakMap<Work, {
  signature: string; ownCandidates: string[]; candidates: string[]; aliases: string[];
  composerTokens: string[];
}>();

const searchTerms = (work: Work) => {
  const signature = JSON.stringify([work.title, work.titleKo, work.catalogue,
    work.composer.name, work.composer.nameKo, work.aliases, work.partOf]);
  const cached = searchTermsCache.get(work);
  if (cached?.signature === signature) return cached;
  const ownCandidates = [
    work.title,
    work.titleKo,
    work.catalogue,
    work.composer.name,
    work.composer.nameKo,
    ...work.aliases,
  ].map(normalize).filter(Boolean);
  const candidates = [
    ...ownCandidates,
    ...(work.partOf ?? []).flatMap((parent) => [
      parent.title,
      parent.titleKo,
      parent.catalogue,
      ...(parent.aliases ?? []),
      ...(parent.position === null ? [] : [`${parent.position}번`, `No. ${parent.position}`]),
    ]),
  ]
    .map(normalize)
    .filter(Boolean);
  const composerTokens = normalize(work.composer.nameKo).split(" ")
    .filter(token => /^[가-힣]{2,}$/.test(token)).sort((a, b) => b.length - a.length);
  const result = { signature, ownCandidates, candidates, aliases: work.aliases.map(normalize), composerTokens };
  searchTermsCache.set(work, result);
  return result;
};

const scoreWork = (work: Work, normalizedQuery: string) => {
  const { ownCandidates, candidates, aliases, composerTokens } = searchTerms(work);

  let score = 0;
  const compactQuery = normalizedQuery.replace(/\s/g, "");
  const queryTokens = normalizedQuery.split(" ").flatMap(token => {
    const prefix = /^[가-힣]+$/.test(token)
      ? composerTokens.find(name => token.length > name.length && token.startsWith(name))
      : undefined;
    return prefix ? [prefix, token.slice(prefix.length)] : [token];
  });
  let complete = queryTokens.every((token) =>
    candidates.some((candidate) => tokenMatches(candidate, token)),
  );
  if (queryTokens.length > 1 && complete) {
    score = 95;
  }
  for (const candidate of candidates) {
    // Korean shorthand often changes spacing; keep numeric/Latin identifiers untouched.
    if (
      /[가-힣]/.test(normalizedQuery) &&
      /[가-힣]/.test(candidate) &&
      candidate.replace(/\s/g, "") === compactQuery
    ) {
      score = Math.max(score, 100);
      complete = true;
    }
    if (candidate === normalizedQuery) score = Math.max(score, 100);
    if (candidate.includes(normalizedQuery)) score = Math.max(score, 80);
    if (normalizedQuery.includes(candidate)) score = Math.max(score, 60);

    const tokenHits = queryTokens.filter((token) => tokenMatches(candidate, token)).length;
    if (queryTokens.length > 1 && tokenHits > 0) {
      score = Math.max(score, tokenHits * 18);
    }
  }

  const shorthandHits = aliases
    .filter(
      (alias) =>
        alias.length > 0 && alias.length <= 12 && normalizedQuery.includes(alias),
    ).length;

  // Prefer the requested member over its collection when their aliases overlap.
  const catalogue = normalize(work.catalogue);
  const catalogueBonus = catalogue && ` ${normalizedQuery} `.includes(` ${catalogue} `)
    ? catalogue.split(" ").length
    : 0;

  const contextPenalty = queryTokens.every(token =>
    ownCandidates.some(candidate => tokenMatches(candidate, token))) ? 0 : 10;
  return { score: score + shorthandHits * 10 + catalogueBonus - contextPenalty, complete };
};

export const findWorksByQueryInList = (items: Work[], query: string) => {
  const normalizedQuery = normalize(query);
  if (!normalizedQuery) return [];
  const ranked = items.map((work) => ({ work, ...scoreWork(work, normalizedQuery) }));
  return ranked
    .filter(({ score, complete }) => score > 0 && complete)
    .sort(
      (a, b) =>
        b.score - a.score ||
        (a.work.popularityRank ?? Number.MAX_SAFE_INTEGER) -
          (b.work.popularityRank ?? Number.MAX_SAFE_INTEGER),
    )
    .map(({ work }) => work);
};

export const findWorksByQuery = (query: string) =>
  findWorksByQueryInList(works, query);

export const getWorkBySlug = (slug: string) =>
  works.find((work) => work.slug === slug) ?? null;

export const getPerformanceById = (id: string) =>
  performances.find((performance) => performance.id === id) ?? null;

export const getPerformancesForWorkFromList = (
  items: Performance[],
  slug: string,
) =>
  items.filter((performance) =>
    performance.program.some((item) => item.workSlug === slug),
  );

export const getPerformancesForWork = (slug: string) =>
  getPerformancesForWorkFromList(performances, slug);

export const getUpcomingPerformancesFromList = (
  items: Performance[],
  now = new Date(),
) => {
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
  return items
    .filter(
      (item) =>
        item.status !== "closed" && (item.endDate ?? item.date) >= today,
    )
    .sort(
      (a, b) =>
        Number(a.date < today) - Number(b.date < today) ||
        `${a.date} ${a.time}`.localeCompare(`${b.date} ${b.time}`),
    );
};

export const getUpcomingPerformances = () =>
  getUpcomingPerformancesFromList(performances);
