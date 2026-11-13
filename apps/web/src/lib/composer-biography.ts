import descriptions from "@/data/composer-descriptions.json";
import { composerIdentityKey, PERIOD_LABELS, type ComposerDirectoryEntry } from "./composer-directory";

const notes = new Map(Object.entries(descriptions).map(([name, item]) => [
  composerIdentityKey(name), { text: item.description, href: "https://www.wikidata.org/wiki/" + item.id, source: "Wikidata" },
]));
for (const [name, text, href, source] of [
  ["Frédéric Chopin", "폴란드의 작곡가이자 피아니스트. 마주르카와 폴로네즈에 폴란드 춤의 리듬을 담았습니다.", "https://chopin.nifc.pl/en/chopin/gatunki/4_mazurki", "쇼팽 연구소"],
  ["Wolfgang Amadeus Mozart", "잘츠부르크에서 태어나 빈에서 활동한 작곡가. 오페라와 교향곡, 피아노 협주곡을 비롯해 여러 장르의 음악을 남겼습니다.", "https://mozarteum.at/en/wolfgang-amade-mozart", "모차르테움 재단"],
  ["Johann Sebastian Bach", "라이프치히의 성 토마스 교회에서 음악을 맡았습니다. 교회력에 맞춰 작곡한 칸타타는 그의 성악 음악을 대표합니다.", "https://www.bach-leipzig.de/en/neutral/bach300-300-years-bach-leipzig", "라이프치히 바흐 아카이브"],
  ["Ludwig van Beethoven", "본에서 태어나 빈에서 활동한 작곡가. 교향곡뿐 아니라 피아노 소나타와 현악 사중주에 걸쳐 작품을 남겼습니다.", "https://www.beethoven.de/en/g/zeittafel-beethoven-in-wien", "본 베토벤하우스"],
]) notes.set(composerIdentityKey(name), { text, href, source });

export function composerBiography(person: ComposerDirectoryEntry, count: number) {
  return notes.get(composerIdentityKey(person.name)) ?? {
    text: person.period !== "other" ? PERIOD_LABELS[person.period] + " 시대의 작곡가입니다."
      : count ? "클래식허블에 이 작곡가의 작품 " + count.toLocaleString("ko") + "개가 등록되어 있습니다." : "아직 등록된 작곡가 소개가 없습니다.",
    href: null, source: null,
  };
}
