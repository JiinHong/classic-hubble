import {
  groupComposers,
  type ComposerDirectoryEntry,
} from "@/lib/composer-directory";

import { ComposerListItem } from "./ComposerListItem";

export function ComposerList({
  composers,
}: {
  composers: ComposerDirectoryEntry[];
}) {
  return (
    <div className="space-y-10">
      {groupComposers(composers).map((group) => (
        <section aria-labelledby={`period-${group.key}`} key={group.key}>
          <div className="mb-2 flex items-baseline justify-between border-b-2 border-stone-950 pb-2">
            <h2
              className="text-lg font-black text-stone-950"
              id={`period-${group.key}`}
            >
              {group.label}
            </h2>
            <span className="text-xs font-bold text-stone-500">
              {group.composers.length}명
            </span>
          </div>
          <ul className="grid grid-cols-1 gap-x-6 sm:grid-cols-2 xl:grid-cols-4">
            {group.composers.map((composer) => (
              <ComposerListItem composer={composer} key={composer.id} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
