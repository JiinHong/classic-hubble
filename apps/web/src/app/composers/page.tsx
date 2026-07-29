import { ComposerDirectory } from "@/components/ComposerDirectory";
import { getComposerDirectory } from "@/lib/catalog";

export const dynamic = "force-dynamic";

export default async function ComposersPage() {
  const composers = await getComposerDirectory();

  return (
    <main>
      <ComposerDirectory composers={composers} />
    </main>
  );
}
