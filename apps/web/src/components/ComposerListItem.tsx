import Link from "next/link";

import {
  composerDiscoveryHref,
  type ComposerDirectoryEntry,
} from "@/lib/composer-directory";

export function ComposerListItem({
  composer,
}: {
  composer: ComposerDirectoryEntry;
}) {
  return (
    <li className="border-b border-stone-200">
      <Link
        className="group block min-h-16 min-w-0 py-3 outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 focus-visible:ring-offset-2"
        href={composerDiscoveryHref(composer)}
        prefetch={false}
      >
        <span className="block text-sm font-bold leading-5 break-words text-stone-950">
          {composer.nameKo}
        </span>
        {composer.nameKo !== composer.name ? (
          <span className="mt-1 block text-xs leading-4 break-words text-stone-500 group-hover:text-emerald-800">
            {composer.name}
          </span>
        ) : null}
      </Link>
    </li>
  );
}
