import { type ButtonHTMLAttributes, forwardRef } from "react";

const variants = {
  primary:
    "bg-violet-600 text-white hover:bg-violet-500 active:bg-violet-700",
  secondary:
    "bg-neutral-800 text-neutral-200 hover:bg-neutral-700 active:bg-neutral-800 border border-neutral-700",
  ghost:
    "bg-transparent text-neutral-400 hover:text-neutral-100 hover:bg-neutral-800/60",
  danger:
    "bg-red-600/80 text-white hover:bg-red-500 active:bg-red-700",
  success:
    "bg-emerald-600 text-white hover:bg-emerald-500 active:bg-emerald-700",
} as const;

const sizes = {
  xs: "px-2 py-1 text-[11px] rounded-md",
  sm: "px-3 py-1.5 text-xs rounded-lg",
  md: "px-4 py-2 text-sm rounded-lg",
  lg: "px-5 py-2.5 text-base rounded-xl",
} as const;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  loading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", loading, disabled, className = "", children, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-medium transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {loading && (
        <span className="mr-2 inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  ),
);
Button.displayName = "Button";

export default Button;
