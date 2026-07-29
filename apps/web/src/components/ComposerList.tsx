import {
  groupComposers,
  selectFeaturedComposers,
  type ComposerDirectoryEntry,
} from "@/lib/composer-directory";

import { ComposerListItem } from "./ComposerListItem";
import { FeaturedComposerCard } from "./FeaturedComposerCard";

export function ComposerList({
  composers,
  showFeatured,
}: {
  composers: ComposerDirectoryEntry[];
  showFeatured: boolean;
}) {
  return (
    <div className="space-y-10">
      {groupComposers(composers).map((group) => {
        const featuredComposers = showFeatured
          ? selectFeaturedComposers(group.composers)
          : [];

        return (
          <section aria-labelledby={`period-${group.key}`} key={group.key}>
            <div className="mb-3 flex items-baseline justify-between border-b-2 border-stone-950 pb-2">
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

            {featuredComposers.length ? (
              <ul
                aria-label={`${group.label} 먼저 만나는 작곡가`}
                className="mb-4 grid grid-cols-2 gap-2 sm:gap-3 xl:grid-cols-4"
              >
                {featuredComposers.map((composer) => (
                  <FeaturedComposerCard composer={composer} key={composer.id} />
                ))}
              </ul>
            ) : null}

            <ul
              aria-label={`${group.label} 전체 작곡가`}
              className="grid grid-cols-2 gap-x-4 sm:gap-x-6 xl:grid-cols-4"
            >
              {group.composers.map((composer) => (
                <ComposerListItem composer={composer} key={composer.id} />
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
