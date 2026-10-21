import type { Work, WorkReference } from "@classic-hubble/shared";

export type WorkComponent = {
  parent_slug: string;
  child_slug: string;
  position: number | null;
  source_url?: string;
};

export function attachWorkComponents(works: Work[], relations: WorkComponent[]): Work[] {
  const index = new Map(works.map((work) => [work.slug, work]));
  const edges = relations.filter(({ parent_slug, child_slug, position }) => {
    const parent = index.get(parent_slug), child = index.get(child_slug);
    return parent && child && parent !== child && parent.composer.id === child.composer.id
      && (position === null || (Number.isInteger(position) && position > 0));
  });
  const graph = new Map<string, string[]>();
  for (const edge of edges) {
    graph.set(edge.parent_slug, [...(graph.get(edge.parent_slug) ?? []), edge.child_slug]);
  }
  const reachable = (start: string, target: string) => {
    const pending = [start], visited = new Set<string>();
    while (pending.length) {
      const node = pending.pop()!;
      if (node === target) return true;
      if (!visited.has(node)) {
        visited.add(node);
        pending.push(...(graph.get(node) ?? []));
      }
    }
    return false;
  };
  const valid = edges.filter(edge => !reachable(edge.child_slug, edge.parent_slug));
  const reference = (slug: string, position: number | null, includeAliases = false): WorkReference => {
    const { title, titleKo, catalogue, aliases } = index.get(slug)!;
    return { slug, title, titleKo, catalogue, position, ...(includeAliases ? { aliases } : {}) };
  };
  const byPosition = (a: WorkReference, b: WorkReference) =>
    (a.position ?? Infinity) - (b.position ?? Infinity) || a.title.localeCompare(b.title);
  const parts = new Map<string, WorkReference[]>(), parents = new Map<string, WorkReference[]>();
  const sources = new Map<string, string>();
  for (const edge of valid) {
    parts.set(edge.parent_slug, [...(parts.get(edge.parent_slug) ?? []), reference(edge.child_slug, edge.position)]);
    parents.set(edge.child_slug, [...(parents.get(edge.child_slug) ?? []), reference(edge.parent_slug, edge.position, true)]);
    if (edge.source_url?.startsWith("https://")) sources.set(edge.child_slug, edge.source_url);
  }
  return works.map(work => ({
    ...work,
    referenceUrl: work.referenceUrl ?? sources.get(work.slug),
    parts: (parts.get(work.slug) ?? []).sort(byPosition),
    partOf: (parents.get(work.slug) ?? []).sort(byPosition),
  }));
}
