// Display only: catalogue titles and search aliases retain their source spelling.
const forms: Record<string, string> = {
  scherzo: "스케르초", ballade: "발라드", prelude: "프렐류드", etude: "에튀드",
  nocturne: "녹턴", mazurka: "마주르카", polonaise: "폴로네즈", waltz: "왈츠",
  valse: "왈츠", impromptu: "즉흥곡", fantasia: "환상곡", fantasy: "환상곡",
  symphony: "교향곡", sinfonia: "신포니아", sonata: "소나타", sonatina: "소나티네",
  concerto: "협주곡", "concerto grosso": "합주 협주곡", "symphonie concertante": "협주 교향곡",
  trio: "삼중주", quartet: "사중주", quartett: "사중주", quintet: "오중주",
  suite: "모음곡", partita: "파르티타", serenade: "세레나데", divertimento: "디베르티멘토",
  fugue: "푸가", "prelude and fugue": "전주곡과 푸가", toccata: "토카타", canon: "카논",
  caprice: "카프리스", bagatelle: "바가텔", rondo: "론도", romance: "로망스",
  rhapsody: "랩소디", "hungarian rhapsody": "헝가리 랩소디", "transcendental etude": "초절기교 에튀드",
  minuet: "미뉴에트", menuet: "미뉴에트", march: "행진곡", overture: "서곡", variations: "변주곡",
  "trio sonata": "트리오 소나타", "church sonata": "교회 소나타", "orchestral suite": "관현악 모음곡",
  mass: "미사곡", requiem: "레퀴엠", cantata: "칸타타", intermezzo: "인터메초",
  bourree: "부레", ecossaise: "에코세즈", barcarolle: "뱃노래", berceuse: "자장가",
  mazurkas: "마주르카집", nocturnes: "녹턴집", polonaises: "폴로네즈집", waltzes: "왈츠집",
  etudes: "에튀드집", preludes: "프렐류드집",
  "marche funebre": "장송 행진곡", "grande polonaise brillante": "화려한 대폴로네즈",
  "andante spianato": "안단테 스피아나토", dumka: "둠카", bolero: "볼레로",
  bourrees: "부레집", contredanse: "콩트르당스", "rondo a la mazur": "마주르카풍 론도",
  andantino: "안단티노", cantabile: "칸타빌레", song: "가곡", polka: "폴카",
  "symphonic poem": "교향시", elegy: "엘레지", invention: "인벤션", oratorio: "오라토리오",
  motet: "모테트", aria: "아리아", gavotte: "가보트", sarabande: "사라방드",
};
const instruments: Record<string, string> = {
  piano: "피아노", keyboard: "건반", violin: "바이올린", cello: "첼로", flute: "플루트",
  viola: "비올라", clarinet: "클라리넷", bassoon: "바순", oboe: "오보에", horn: "호른",
  harp: "하프", organ: "오르간", trumpet: "트럼펫", string: "현악", strings: "현악",
  harpsichord: "하프시코드", continuo: "통주저음", orchestra: "관현악", recorder: "리코더",
  cornet: "코넷", "alto saxophone": "알토 색소폰", "double bass": "콘트라베이스",
  "string orchestra": "현악 합주", "low strings": "저음 현악기", winds: "관악기",
};
const fold = (s: string) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
const get = (dict: Record<string, string>, key: string) => Object.hasOwn(dict, key) ? dict[key] : undefined;
const pitches: Record<string, string> = { C: "다", D: "라", E: "마", F: "바", G: "사", A: "가", B: "나" };
function pitch(note: string, acc: string | undefined, minor: boolean) {
  return (acc === "flat" ? "내림" : acc === "sharp" ? "올림" : "") + pitches[note.toUpperCase()] + (minor ? "단조" : "장조");
}

function notation(value: string) {
  return value.trim().replace(/\s+/g, " ")
    .replace(/^prelude(?= (?:no\.?|in |op\.)|,)/i, "Prélude").replace(/^etude(?= (?:no\.?|in |op\.)|,)/i, "Étude")
    .replace(/\b(?:no|nr)\.?\s*(?=\d)/gi, "No. ").replace(/\bop(?:us)?\.?\s*(?=\d|posth\b)/gi, "Op. ")
    .replace(/\b([KDSBLMH])\.\s*(?=\d)/g, "$1. ").replace(/\b(BWV|HWV|RV|WoO|WWV|WAB)\s*(?=\d)/g, "$1 ")
    .replace(/\b([a-g])(?:[- ]?(flat|sharp)|([♭♯#]))?\s+(major|minor)\b/gi,
      (_, note: string, word: string, symbol: string, mode: string) =>
        note.toUpperCase() + (word ? "-" + word.toLowerCase() : symbol ? symbol === "♭" ? "-flat" : "-sharp" : "") + " " + mode.toLowerCase())
    .replace(/\b(major|minor)\s+(?=Op\. \d)/g, "$1, ")
    .replace(/(\bOp\. (?:posth\.? )?\d+[a-z]?),\s*(?=No\. \d)/gi, "$1 ")
    .replace(/(\d),$/, "$1");
}
// Match complete catalogue tokens: Op. 2 is not Op. 20, nor Op. 10 No. 1 No. 10.
const cataloguePattern = /(?:Op\. posth\.(?! \[?\d)|(?:Op\.|[KGJDSBLMH]\.|BWV|RV|HWV|WoO|WWV|WAB|FP) (?:(?:posth|Anh)\.? )?\[?\d+[a-z]?\]?(?:[/:.-]\d+[a-z]?)*(?:,? No\. \d+\/?[a-z]?)?|KK (?:Anh\. )?[IVX]+[a-z]?(?:\/\d+)?|Hob\. [IVX]+[a-z]?:\d+[a-z]?)/.source;
const catalogueToken = new RegExp("\\b" + cataloguePattern, "gi");
function withCatalogue(title: string, catalogue: string) {
  if (!catalogue) return title;
  const tokens = [...title.matchAll(catalogueToken)];
  const key = (s: string) => s.toLowerCase().replace(/posth\.? /, "").replace(/[[\],]/g, "").replace(/(\d)\/([a-z])$/, "$1$2");
  for (const match of tokens) {
    const have = key(match[0]), want = key(catalogue);
    if (have === want || have.startsWith(want + " no. ")) return title;
    if (want.startsWith(have + " no. ")) {
      const end = match.index + match[0].length;
      return title.slice(0, end) + catalogue.slice(catalogue.lastIndexOf(" No.")) + title.slice(end);
    }
  }
  const at = title.toLowerCase().indexOf(catalogue.toLowerCase());
  if (at >= 0 && !/[\p{L}\d]/u.test(title.charAt(at - 1)) &&
      !/[\p{L}\d/]/u.test(title.charAt(at + catalogue.length))) return title;
  return title + ", " + catalogue;
}
function endsWithFinal(s: string) { return (s.charCodeAt(s.length - 1) - 0xac00) % 28 !== 0; }
function scoring(value: string) {
  const count: Record<string, string> = { "2": "두", two: "두", "3": "세", three: "세", "4": "네", four: "네" };
  const names: string[] = [];
  for (const part of value.split(/,? and | & |, /)) {
    const counted = /^(2|3|4|two|three|four) (.+)s$/.exec(part);
    const instrument = get(instruments, counted ? counted[2] : part);
    if (!instrument) return;
    names.push(counted ? count[counted[1]] + " 대의 " + instrument : instrument);
  }
  if (names.length < 2) return names[0];
  const last = names.pop();
  const first = names.join(", ");
  return first + (endsWithFinal(first) ? "과 " : "와 ") + last;
}
function translateForm(name: string): string | undefined {
  const n = fold(name), exact = get(forms, n);
  if (exact) return exact;
  const counted = /^(\d+) (.+)$/.exec(n);
  if (counted && get(forms, counted[2])?.endsWith("집")) return counted[1] + "개의 " + forms[counted[2]].slice(0, -1);
  const [instrument, kind] = n.split(" ");
  if (n === instrument + " " + kind && get(instruments, instrument) && /^(sonata|sonatina|concerto|trio|quartet|quintet)$/.test(kind))
    return instruments[instrument] + " " + forms[kind];
  const [form, soloist] = n.split(" for ");
  const soloistKo = soloist && scoring(soloist);
  if (soloistKo && n === form + " for " + soloist && get(forms, form)) {
    const solo = /^(.+) and orchestra$/.exec(soloist);
    if (form === "concerto" && solo && get(instruments, solo[1])) return instruments[solo[1]] + " 협주곡";
    const particle = endsWithFinal(soloistKo) ? "을" : "를";
    return soloistKo + particle + " 위한 " + forms[form];
  }
}

// Consume the whole title. A subtitle such as ": II. Scherzo" or "on a theme
// from ..." describes a different thing and must never silently disappear.
const formalTitle = new RegExp("^(.+?)(?=,? (?:\\[?No\\. |in [A-G]|" + cataloguePattern + ")|$)(.*)$", "i");
const leadingCatalogue = new RegExp("^,? (" + cataloguePattern + ")(?=$|[ ,])", "i");
const parenthesizedCatalogue = new RegExp(" \\((" + cataloguePattern + ")\\)", "gi");
function parseFormal(title: string) {
  const cycle = /^Étude No\. ([123]) from Trois nouvelles études in [A-G](?:-(?:flat|sharp))? (?:minor|major)$/i.exec(title);
  if (cycle) return { form: "세 개의 새로운 에튀드 중", number: cycle[1], tonalKey: "", cat: "", nickname: "" };
  const quoted = /,? ["“]([^"“”]+)["”](?= in [A-G]|$)/.exec(title);
  const plain = (quoted ? title.replace(quoted[0], "") : title).replace(parenthesizedCatalogue, ", $1");
  const [, name, suffix] = formalTitle.exec(plain) ?? [];
  const form = name && translateForm(name);
  if (!form) return;
  let rest = suffix, number = "", tonalKey = "", cat = "";
  while (rest) {
    const ordinal = /^,? (?:No\. (\d+[a-z]?)|\[No\. (\d+[a-z]?)\])(?=$|[ ,])/i.exec(rest);
    const tonal = /^,? in ([A-G])(?:-(flat|sharp))? (major|minor)(?=$|[ ,])/i.exec(rest);
    const identifier = leadingCatalogue.exec(rest);
    if (ordinal && !number && !cat) { number = ordinal[1] || ordinal[2]; rest = rest.slice(ordinal[0].length); }
    else if (tonal && !tonalKey) { tonalKey = pitch(tonal[1], tonal[2], tonal[3] === "minor"); rest = rest.slice(tonal[0].length); }
    else if (identifier) { cat ||= identifier[1]; rest = rest.slice(identifier[0].length); }
    else return;
  }
  return { form, number, tonalKey, cat, nickname: quoted?.[1] ?? "" };
}

const koreanFormSpelling: Record<string, string> = { 야상곡: "녹턴", 전주곡: "프렐류드", 연습곡: "에튀드", 폴로네이즈: "폴로네즈" };
function koreanHeading(value: string) {
  return notation(value).replace(/^(야상곡|전주곡|연습곡|폴로네이즈)(?=\s+\d|\s+제\s*\d|\s+Op\.|,|$)/, m => koreanFormSpelling[m])
    .replace(/플룻(?=$|[\s,·])/g, "플루트")
    .replace(/(?<!\d)([2-9])중주/g, (_, n: string) => "이삼사오육칠팔구"[Number(n) - 2] + "중주")
    .replace(/ +제\s*(\d+)\s*번/g, " $1번")
    .replace(/(?:^|(?<=\s))([a-g])([♭♯#]?)(장조|단조)/gi,
      (_, n, a, mode) => pitch(n, a === "♭" ? "flat" : a ? "sharp" : "", mode === "단조"));
}
export function workDisplay(title: string, titleKo?: string | null, catalogue?: string | null) {
  const original = notation(title), cat = notation(catalogue ?? "");
  const full = withCatalogue(original, cat);
  const parsed = parseFormal(original);
  let heading = titleKo && /[가-힣]/.test(titleKo) ? koreanHeading(titleKo) : "";
  if (parsed) {
    const { form, number, tonalKey, cat: embedded } = parsed;
    // Shorten existing numbered labels only when the omitted details also
    // appear in the original line. Preserve nicknames, editions and scoring.
    if (heading.startsWith(form + " ") || heading.startsWith(form + ", ")) {
      const tail = heading.slice(form.length).replace(/^,? /, "");
      const numbered = /^(\d+[a-z]?)번(.*)$/.exec(tail);
      if (numbered && (!number || number === numbered[1])) {
        let details = numbered[2].trim();
        if (tonalKey && details.startsWith(tonalKey)) details = details.slice(tonalKey.length).trim();
        details = details.replace(/^,\s*/, "");
        if (!details || details === cat || details === embedded) heading = form + " " + numbered[1] + "번";
      } else if (number && cat && tail.replace(/,\s*(\d+)번$/, " No. $1") === cat) heading = form + " " + number + "번";
    }
    if (!heading) heading = [form, number ? number + "번" : tonalKey || (/^\d+개의 /.test(form) ? "" : embedded || cat),
      parsed.nickname && "‘" + parsed.nickname + "’"].filter(Boolean).join(" ");
  }
  heading ||= original;
  return { heading, subtitle: heading === original ? (full === original ? "" : cat) : full };
}
