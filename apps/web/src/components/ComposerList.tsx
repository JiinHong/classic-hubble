import { ChevronDown } from "lucide-react";
import { useState } from "react";

import {
  groupComposers,
  selectFeaturedComposers,
  type ComposerDirectoryEntry,
} from "@/lib/composer-directory";

import { ComposerListItem } from "./ComposerListItem";
import { FeaturedComposerCard } from "./FeaturedComposerCard";

export function ComposerList({
  composers,
  searching,
}: {
  composers: ComposerDirectoryEntry[];
  searching: boolean;
}) {
  const [otherOpen, setOtherOpen] = useState(false);
  return (
    <div className="space-y-10">
      {groupComposers(composers).map((group, groupIndex) => {
        const featuredComposers = !searching
          ? selectFeaturedComposers(group.composers)
          : [];
        const featuredIds = new Set(
          featuredComposers.map((composer) => composer.id),
        );
        const plainComposers = !searching
          ? group.composers.filter((composer) => !featuredIds.has(composer.id))
          : group.composers;

        const collapsible = group.key === "other" && !searching;
        const expanded = !collapsible || otherOpen;
        const count = (
          <span className="text-xs font-bold text-stone-500">
            {group.composers.length}명
          </span>
        );
        return (
          <section aria-labelledby={`period-${group.key}`} key={group.key}>
            {collapsible ? (
              <h2 id="period-other" className="mb-3 border-b-2 border-stone-950">
                <button
                  type="button"
                  aria-label={group.label}
                  aria-expanded={otherOpen}
                  aria-controls="period-other-list"
                  onClick={() => setOtherOpen((open) => !open)}
                  className="flex min-h-11 w-full items-center gap-2 pb-2 text-left text-lg font-black text-stone-950"
                >
                  <span className="mr-auto">{group.label}</span>
                  {count}
                  <ChevronDown aria-hidden="true" className={`size-4 text-stone-500 ${otherOpen ? "rotate-180" : ""}`} />
                </button>
              </h2>
            ) : (
              <div className="mb-3 flex items-baseline justify-between border-b-2 border-stone-950 pb-2">
                <h2 className="text-lg font-black text-stone-950" id={`period-${group.key}`}>{group.label}</h2>
                {count}
              </div>
            )}
            <div id={`period-${group.key}-list`} hidden={!expanded}>
              {expanded && featuredComposers.length ? (
                <ul
                  aria-label={`${group.label} 먼저 만나는 작곡가`}
                  className="mb-4 grid grid-cols-2 gap-2 sm:gap-3 md:grid-cols-3 xl:grid-cols-4"
                >
                  {featuredComposers.map((composer, featuredIndex) => (
                    <FeaturedComposerCard
                      composer={composer}
                      eager={groupIndex === 0 && featuredIndex === 0}
                      key={composer.id}
                    />
                  ))}
                </ul>
              ) : null}

              {expanded && plainComposers.length ? (
                <ul
                  aria-label={`${group.label} 작곡가 목록`}
                  className="grid grid-cols-2 gap-x-4 sm:gap-x-6 xl:grid-cols-4"
                >
                  {plainComposers.map((composer) => (
                    <ComposerListItem composer={composer} key={composer.id} />
                  ))}
                </ul>
              ) : null}
            </div>
          </section>
        );
      })}
    </div>
  );
}
