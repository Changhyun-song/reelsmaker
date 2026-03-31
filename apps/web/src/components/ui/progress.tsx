interface LinearProgressProps {
  value: number;
  size?: "sm" | "md" | "lg";
  color?: string;
  className?: string;
}

export function LinearProgress({
  value,
  size = "md",
  color = "bg-violet-500",
  className = "",
}: LinearProgressProps) {
  const h = size === "sm" ? "h-1" : size === "lg" ? "h-3" : "h-2";
  return (
    <div className={`w-full rounded-full bg-neutral-800 ${h} ${className}`}>
      <div
        className={`${h} rounded-full ${color} transition-all duration-500`}
        style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
      />
    </div>
  );
}

interface CircularProgressProps {
  value: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
  children?: React.ReactNode;
}

export function CircularProgress({
  value,
  size = 80,
  strokeWidth = 6,
  className = "",
  children,
}: CircularProgressProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(value, 100) / 100) * circumference;

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-neutral-800"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="text-violet-500 transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        {children ?? <span className="text-sm font-bold text-neutral-200">{Math.round(value)}%</span>}
      </div>
    </div>
  );
}
