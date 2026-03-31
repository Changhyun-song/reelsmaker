"use client";

interface Tab {
  key: string;
  label: string;
  icon?: React.ReactNode;
  count?: number;
}

interface TabsProps {
  tabs: Tab[];
  active: string;
  onChange: (key: string) => void;
  variant?: "underline" | "pill";
  className?: string;
}

export default function Tabs({ tabs, active, onChange, variant = "pill", className = "" }: TabsProps) {
  if (variant === "underline") {
    return (
      <div className={`flex gap-1 border-b border-neutral-800 ${className}`}>
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => onChange(t.key)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              active === t.key
                ? "border-violet-500 text-violet-400"
                : "border-transparent text-neutral-500 hover:text-neutral-300"
            }`}
          >
            {t.icon && <span className="mr-1.5">{t.icon}</span>}
            {t.label}
            {t.count != null && (
              <span className="ml-1.5 text-[10px] rounded-full bg-neutral-800 px-1.5 py-0.5">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className={`inline-flex gap-1 rounded-xl bg-neutral-900 p-1 ${className}`}>
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={`px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
            active === t.key
              ? "bg-violet-600 text-white shadow-sm"
              : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800"
          }`}
        >
          {t.icon && <span className="mr-1">{t.icon}</span>}
          {t.label}
        </button>
      ))}
    </div>
  );
}
