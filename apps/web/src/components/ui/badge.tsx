const STATUS_MAP: Record<string, string> = {
  draft: "bg-neutral-800 text-neutral-300",
  drafted: "bg-neutral-800 text-neutral-300",
  queued: "bg-yellow-900/50 text-yellow-400",
  running: "bg-blue-900/50 text-blue-400 animate-pulse",
  completed: "bg-emerald-900/50 text-emerald-400",
  failed: "bg-red-900/50 text-red-400",
  ready: "bg-emerald-900/50 text-emerald-400",
  pending: "bg-neutral-800 text-neutral-400",
  generating: "bg-violet-900/50 text-violet-400 animate-pulse",
  approved: "bg-purple-900/50 text-purple-400",
  structured: "bg-emerald-900/50 text-emerald-400",
  needs_revision: "bg-orange-900/50 text-orange-400",
};

interface BadgeProps {
  status: string;
  label?: string;
  className?: string;
}

export default function Badge({ status, label, className = "" }: BadgeProps) {
  const style = STATUS_MAP[status] ?? "bg-neutral-800 text-neutral-400";
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${style} ${className}`}>
      {label ?? status}
    </span>
  );
}
