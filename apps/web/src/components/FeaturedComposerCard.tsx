import Image from "next/image";
import Link from "next/link";

import {
  composerDiscoveryHref,
  type ComposerDirectoryEntry,
} from "@/lib/composer-directory";

export function FeaturedComposerCard({
  composer,
}: {
  composer: ComposerDirectoryEntry;
}) {
  if (!composer.portraitSrc) return null;

  return (
    <li className="min-w-0">
      <Link
        className="group flex h-28 min-w-0 items-center gap-2 rounded-md border border-stone-200 bg-white p-2.5 outline-none transition hover:border-stone-400 hover:shadow-sm focus-visible:ring-2 focus-visible:ring-emerald-700 focus-visible:ring-offset-2 sm:gap-3 sm:p-3"
        href={composerDiscoveryHref(composer)}
      >
        <span className="relative size-12 shrink-0 overflow-hidden rounded-full bg-stone-200 sm:size-16">
          <Image
            alt=""
            className="object-cover object-top grayscale transition duration-300 group-hover:grayscale-0"
            fill
            sizes="(max-width: 639px) 48px, 64px"
            src={composer.portraitSrc}
          />
        </span>
        <span className="min-w-0">
          <span className="block text-xs font-black leading-5 break-keep text-stone-950 sm:text-sm">
            {composer.nameKo}
          </span>
          {composer.nameKo !== composer.name ? (
            <span className="mt-1 hidden text-xs leading-4 text-stone-500 group-hover:text-emerald-800 sm:line-clamp-2">
              {composer.name}
            </span>
          ) : null}
        </span>
      </Link>
    </li>
  );
}
