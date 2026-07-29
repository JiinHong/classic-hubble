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
        className="group block min-h-16 py-3 outline-none focus-visible:ring-2 focus-visible:ring-emerald-700 focus-visible:ring-offset-2"
        href={composerDiscoveryHref(composer)}
      >
        <span className="flex items-center gap-2">
          <span
            className={`text-sm text-stone-950 ${
              composer.isCore ? "font-black" : "font-bold"
            }`}
          >
            {composer.nameKo}
          </span>
          {composer.isCore ? (
            <span className="border border-rose-200 bg-rose-50 px-1.5 py-0.5 text-[10px] font-black text-rose-700">
              핵심
            </span>
          ) : null}
        </span>
        {composer.nameKo !== composer.name ? (
          <span className="mt-1 block text-xs text-stone-500 group-hover:text-emerald-800">
            {composer.name}
          </span>
        ) : null}
      </Link>
    </li>
  );
}
