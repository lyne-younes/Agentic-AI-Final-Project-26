import { LoaderCircle } from "lucide-react";
import type { ButtonHTMLAttributes, Ref } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "accent" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  iconOnly?: boolean; // requires an aria-label
  ref?: Ref<HTMLButtonElement>;
}

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  iconOnly = false,
  type = "button",
  disabled,
  className,
  children,
  ...rest
}: ButtonProps) {
  const classes = [
    "btn",
    `btn-${variant}`,
    size !== "md" && `btn-${size}`,
    iconOnly && "btn-icon",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button type={type} className={classes} disabled={disabled || loading} {...rest}>
      {loading && <LoaderCircle size={16} className="spin" aria-hidden="true" />}
      {children}
    </button>
  );
}
