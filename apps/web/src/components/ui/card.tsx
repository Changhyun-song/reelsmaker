import type { ReactNode, HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: "default" | "interactive" | "highlighted";
  padding?: "none" | "sm" | "md" | "lg";
}

export default function Card({
  children,
  variant = "default",
  padding = "md",
  className = "",
  ...props
}: CardProps) {
  const base = "rounded-xl border";
  const variantStyles = {
    default: "border-neutral-800 bg-neutral-900/50",
    interactive: "border-neutral-800 bg-neutral-900/50 hover:border-neutral-600 hover:bg-neutral-900 transition cursor-pointer",
    highlighted: "border-violet-700/50 bg-violet-950/20",
  };
  const paddings = {
    none: "",
    sm: "p-3",
    md: "p-5",
    lg: "p-6",
  };

  return (
    <div className={`${base} ${variantStyles[variant]} ${paddings[padding]} ${className}`} {...props}>
      {children}
    </div>
  );
}
