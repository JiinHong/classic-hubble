import { classify, formLabels, type Form } from "./work-forms";
import { validComponentEdges, type WorkComponent } from "./work-components";
export { classify } from "./work-forms";
export type WorkRow = { slug: string; title: string; title_ko: string | null; catalogue: string | null; instrumentation?: string | null };
export type WorkNode = WorkRow & { parts: WorkNode[]; alternate?: WorkRow };
const collator = new Intl.Collator("ko", { numeric: true, sensitivity: "base" });
const compareTitle = (a: WorkRow,b: WorkRow) => collator.compare(a.title_ko || a.title, b.title_ko || b.title) || a.slug.localeCompare(b.slug);
const highlights: Record<string, Form[]> = {
  "Frédéric Chopin": ["prelude", "etude", "scherzo", "ballade", "piano-concerto", "nocturne", "mazurka"],
  "Wolfgang Amadeus Mozart": ["symphony", "piano-concerto", "opera", "piano-sonata", "violin-concerto", "string-quartet", "serenade"],
};

export function repertoire(rows: WorkRow[], relations: WorkComponent[], genre: Form | undefined, page: number, size: number, composerName = "") {
  const index = new Map(rows.map(row => [row.slug, { ...row, parts: [] } as WorkNode]));
  const position = (edge: WorkComponent) => edge.position ?? (classify(index.get(edge.child_slug)!) === "overture" ? 0 : Infinity);
  const edges = validComponentEdges(relations, (p,c) => index.has(p) && index.has(c))
    .sort((a,b) => position(a) - position(b) || compareTitle(index.get(a.child_slug)!, index.get(b.child_slug)!));
  const children = new Set<string>();
  for (const edge of edges) {
    const parent = index.get(edge.parent_slug)!, child = index.get(edge.child_slug)!;
    if (!parent.parts.includes(child)) parent.parts.push(child);
    children.add(child.slug);
  }
  // Both identities document movement III of Op. 35. Keep both detail URLs;
  // never infer equivalence from a shared title or tempo.
  const sonata = index.get("wikidata-q284448");
  const march = sonata?.parts.find(w => w.slug === "component-wikidata-q284448-3");
  const alternate = sonata?.parts.find(w => w.slug === "wikidata-q116431346");
  if (sonata && march && alternate) {
    march.alternate = alternate;
    sonata.parts = sonata.parts.filter(w => w !== alternate);
  }
  const roots = [...index.values()].filter(row => !children.has(row.slug));
  const groups = new Map<Form,WorkNode[]>();
  for (const root of roots) {
    const form = classify(root);
    const group = groups.get(form) ?? [];
    group.push(root);
    groups.set(form, group);
  }
  const priority = new Map((highlights[composerName] ?? []).map((id,i) => [id,i]));
  const facets = [...groups].map(([id,group]) => ({ id, label: formLabels.get(id)!, count: group.length }))
    .sort((a,b) => (priority.get(a.id) ?? Infinity) - (priority.get(b.id) ?? Infinity)
      || Number(a.id === "other") - Number(b.id === "other") || b.count - a.count || collator.compare(a.label,b.label));
  const selected = genre ? (groups.get(genre) ?? []).sort((a,b) =>
    a.catalogue && b.catalogue ? collator.compare(a.catalogue,b.catalogue) || compareTitle(a,b)
    : Number(!a.catalogue) - Number(!b.catalogue) || compareTitle(a,b)) : roots;
  return { count: roots.length, componentCount: children.size - Number(!!march && !!alternate), selectedCount: selected.length, facets, works: selected.slice((page-1)*size,page*size) };
}
