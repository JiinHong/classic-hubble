import {
  PERIOD_OPTIONS,
  type ComposerPeriodKey,
} from "@/lib/composer-directory";

type ComposerPeriodFilterProps = {
  onChange: (period: "all" | ComposerPeriodKey) => void;
  value: "all" | ComposerPeriodKey;
};

export function ComposerPeriodFilter({
  onChange,
  value,
}: ComposerPeriodFilterProps) {
  return (
    <div
      aria-label="시대"
      className="flex overflow-x-auto border-y border-stone-200"
      role="group"
    >
      {PERIOD_OPTIONS.map((option) => (
        <button
          aria-pressed={value === option.key}
          className={`h-11 shrink-0 border-r border-stone-200 px-4 text-sm font-bold transition ${
            value === option.key
              ? "bg-stone-950 text-white"
              : "bg-white text-stone-600 hover:bg-stone-100 hover:text-stone-950"
          }`}
          key={option.key}
          onClick={() => onChange(option.key)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
