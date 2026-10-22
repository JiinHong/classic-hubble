import type { ProgramSource } from "@classic-hubble/shared";
import { BadgeCheck, CircleHelp, Eye, ScanSearch, ShieldCheck } from "lucide-react";

import { confidenceLabel, sourceTone } from "@/lib/format";

const icons = {
  official: ShieldCheck,
  verified: BadgeCheck,
  ocr: ScanSearch,
  estimated: Eye,
  unknown: CircleHelp,
};

type ConfidenceBadgeProps = {
  source: ProgramSource;
};

export function ConfidenceBadge({ source }: ConfidenceBadgeProps) {
  const Icon = icons[source.type];

  return (
    <span
      className={`inline-flex min-h-7 items-center gap-1.5 rounded-md border px-2 text-xs font-semibold ${sourceTone(
        source.type,
      )}`}
    >
      <Icon aria-hidden="true" className="size-3.5" />
      <span>{source.label}</span>
      {source.confidence !== null && (
        <span className="tabular-nums">{confidenceLabel(source.confidence)}</span>
      )}
    </span>
  );
}
