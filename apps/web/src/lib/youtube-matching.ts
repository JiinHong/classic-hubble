import type { Work } from "@classic-hubble/shared";

export type YouTubeMatchReason =
  | "composer_catalogue"
  | "composer_title"
  | "distinctive_title";
export type YouTubeWorkEntry = {
  text: string;
  timestamp?: string;
  ambiguous: boolean;
  candidates: { work: Work; reason: YouTubeMatchReason }[];
};
const cataloguePattern =
  /\b(?:op|bwv|hwv|kv|k|rv|d|s|l|woo)\.?\s*\d+[a-z]?(?:\s*(?:\/|,?\s*(?:no|nr)\.?)\s*\d+[a-z]?)?\b/gi;
const workNumber = /\bno\.?\s*(\d+)\b|(?:제\s*)?(\d+)\s*(?:번|곡)/gi;
const musicalKey =
  /\bin\s+([a-g](?:[- ]?(?:flat|sharp)|[#♭♯])?\s+(?:major|minor))\b/gi;
const generic =
  /^(?:adagio|allegro|andante|presto|largo|vivace|moderato|finale|intermezzo|aria|menuet|minuet|아다지오|알레그로|안단테)$/;
const normalize = (value: string) =>
  value
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .normalize("NFC")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim()
    .replace(/\s+/g, " ");
const contains = (text: string, term: string) =>
  Boolean(term) && ` ${text} `.includes(` ${term} `);
const catalogueKey = (value: string) =>
  normalize(
    value
      .replace(/\bkv\b/gi, "K")
      .replace(/\/\s*(\d+)/g, " No. $1")
      .replace(/\bnr\b/gi, "No"),
  ).replace(/ /g, "");
const catalogues = (text: string) =>
  [...text.matchAll(cataloguePattern)].map((match) => catalogueKey(match[0]));
const numbers = (text: string) =>
  [...text.replace(cataloguePattern, "").matchAll(workNumber)].map(
    (match) => match[1] ?? match[2],
  );
const keys = (text: string) =>
  [...text.matchAll(musicalKey)].map((match) => normalize(match[1]));

type IndexedWork = {
  work: Work;
  names: string[];
  catalogue: string;
  numbers: string[];
  keys: string[];
};
function indexWorks(works: Work[]) {
  const composers = new Map<string, { full: string[]; short: string[] }>();
  const childPositions = new Map<string, Set<string>>();
  const items: IndexedWork[] = works.map((work) => {
    for (const parent of work.partOf ?? []) {
      if (parent.position === null) continue;
      const positions = childPositions.get(parent.slug) ?? new Set<string>();
      positions.add(String(parent.position));
      childPositions.set(parent.slug, positions);
    }
    const full = [work.composer.name, work.composer.nameKo]
      .map(normalize)
      .filter(Boolean);
    composers.set(work.composer.id, {
      full,
      short: full
        .map((name) => name.split(" ").at(-1)!)
        .filter((name) => name.length >= 2),
    });
    const composerNames = [
      ...full,
      ...full.map((name) => name.split(" ").at(-1)!),
    ];
    return {
      work,
      names: [
        ...new Set([work.title, work.titleKo, ...work.aliases].map(normalize)),
      ].filter((name) => name && !composerNames.includes(name)),
      catalogue: catalogueKey(work.catalogue),
      numbers: numbers(work.title),
      keys: keys(work.title),
    };
  });
  return { items, composers: [...composers], childPositions };
}
const indexes = new WeakMap<Work[], ReturnType<typeof indexWorks>>();

export function identifyYouTubeWorks(
  video: { title: string; description: string },
  works: Work[],
): { entries: YouTubeWorkEntry[] } {
  let index = indexes.get(works);
  if (!index) {
    index = indexWorks(works);
    indexes.set(works, index);
  }
  const composerIds = (text: string) => {
    const value = normalize(text);
    const entries = index.composers;
    const full = entries.filter(([, names]) =>
      names.full.some((name) => contains(value, name)),
    );
    return new Set(
      (full.length
        ? full
        : entries.filter(([, names]) =>
            names.short.some((name) => contains(value, name)),
          )
      ).map(([id]) => id),
    );
  };
  const credits = video.description
    .split(/\r?\n/)
    .filter((line) => /^(?:composer|composed by|작곡(?:가)?)\s*:/i.test(line));
  const creditIds = composerIds(credits.join(" "));
  const titleIds = composerIds(video.title);
  const contextIds =
    creditIds.size === 1
      ? creditIds
      : titleIds.size === 1
        ? titleIds
        : new Set<string>();
  const segments = [
    ...video.title
      .split(/\s*[;；]\s*/)
      .map((text) => ({ text, source: "title" })),
    ...video.description
      .split(/\r?\n|\s*[;；]\s*/)
      .map((text) => ({ text, source: "description" })),
  ];
  const entries: YouTubeWorkEntry[] = [];
  const seen = new Set<string>();
  const titleWorkSlugs = new Set<string>();
  for (const segment of segments) {
    const text = segment.text.trim();
    if (!text || text.length > 400) continue;
    const timestamp = text.match(
      /^\s*\[?((?:\d{1,2}:)?\d{1,3}:\d{2})\]?\s*/,
    )?.[1];
    if (
      segment.source === "description" &&
      !timestamp &&
      (/https?:\/\/|www\.|\b(?:favorite|discuss|subscribe|follow|biography|studied|inspired|recommended)\b|구독|레슨|인터뷰|작곡가\s*:/i.test(
        text,
      ) ||
        /^(?:composer|composed by)\s*:/i.test(text))
    )
      continue;
    const normalized = normalize(text);
    const ordinal = text
      .replace(/^\s*\[?(?:\d{1,2}:)?\d{1,3}:\d{2}\]?\s*/, "")
      .match(/^\s*(I{1,3}|IV|V|VI{1,3}|IX|X|\d{1,2})[.)]\s+/i)?.[1];
    const movementPosition = ordinal
      ? /^\d+$/.test(ordinal)
        ? Number(ordinal)
        : ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"].indexOf(
            ordinal.toUpperCase(),
          ) + 1
      : null;
    const explicitIds = composerIds(text);
    const composer = explicitIds.size ? explicitIds : contextIds;
    const inputCatalogues = catalogues(text);
    if (
      inputCatalogues.length > 1 ||
      /\b(?:op|bwv|hwv|kv|k|rv|d|s|woo)\.?\s*\d+\s*[-–—]\s*\d+/i.test(text)
    )
      continue;
    const inputNumbers = numbers(text),
      inputKeys = keys(text);
    const found: { work: Work; reason: YouTubeMatchReason; rank: number }[] =
      [];
    for (const item of index.items) {
      const { work } = item;
      if (
        segment.source === "description" &&
        movementPosition !== null &&
        !work.partOf?.some(
          (parent) =>
            titleWorkSlugs.has(parent.slug) &&
            parent.position === movementPosition,
        )
      )
        continue;
      if (composer.size && !composer.has(work.composer.id)) continue;
      const component = work.partOf?.find(
        (parent) =>
          parent.position !== null &&
          inputNumbers.includes(String(parent.position)) &&
          [parent.title, parent.titleKo, ...(parent.aliases ?? [])].some(
            (name) => contains(normalized, normalize(name)),
          ),
      );
      if (
        !component &&
        inputNumbers.length &&
        item.numbers.length &&
        inputNumbers.some((n) => !item.numbers.includes(n))
      )
        continue;
      if (
        inputKeys.length &&
        item.keys.length &&
        inputKeys.some((key) => !item.keys.includes(key))
      )
        continue;
      if (inputCatalogues.length && !inputCatalogues.includes(item.catalogue))
        continue;
      const hasComposer = composer.has(work.composer.id);
      const name = item.names.find(
        (name) =>
          name.length >= (hasComposer ? 2 : 3) && contains(normalized, name),
      );
      let reason: YouTubeMatchReason;
      if (hasComposer && inputCatalogues.length && item.catalogue)
        reason = "composer_catalogue";
      else if (hasComposer && (name || component)) reason = "composer_title";
      else if (
        !composer.size &&
        name &&
        !generic.test(name) &&
        !/^(?:symphony|concerto|sonata|교향곡|협주곡|소나타)\b/.test(name) &&
        name.length >= 5
      )
        reason = "distinctive_title";
      else continue;
      // A collection title plus an explicit piece number must not select the collection.
      if (
        work.parts?.length &&
        inputNumbers.length &&
        !item.numbers.length &&
        !inputCatalogues.length
      )
        continue;
      const parentOfNumbered = inputNumbers.some((number) =>
        index.childPositions.get(work.slug)?.has(number),
      );
      if (parentOfNumbered && !inputCatalogues.length) continue;
      found.push({
        work,
        reason,
        rank:
          (reason === "composer_catalogue"
            ? 30
            : reason === "composer_title"
              ? 20
              : 10) +
          (component ? 5 : 0) +
          (name ? Math.min(name.length / 100, 1) : 0),
      });
    }
    found.sort(
      (a, b) => b.rank - a.rank || a.work.slug.localeCompare(b.work.slug),
    );
    const unshown = found.filter((candidate) => !seen.has(candidate.work.slug));
    if (!unshown.length) continue;
    const candidates = unshown
      .slice(0, 3)
      .map(({ work, reason }) => ({ work, reason }));
    if (segment.source === "title" && unshown.length === 1)
      titleWorkSlugs.add(candidates[0].work.slug);
    candidates.forEach((candidate) => seen.add(candidate.work.slug));
    entries.push({
      text,
      timestamp,
      ambiguous: unshown.length > 1,
      candidates,
    });
  }
  return { entries };
}
