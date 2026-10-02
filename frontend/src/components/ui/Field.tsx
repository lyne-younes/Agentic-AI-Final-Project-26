import type { ReactNode } from "react";

interface FieldProps {
  label: string;
  htmlFor: string;
  children: ReactNode;
  hint?: string;
  error?: string | null;
  required?: boolean;
}

export function Field({ label, htmlFor, children, hint, error, required = false }: FieldProps) {
  return (
    <div className="field">
      <label htmlFor={htmlFor}>
        {label}
        {required && (
          <span className="required" aria-hidden="true">
            {" "}
            *
          </span>
        )}
      </label>
      {children}
      {error ? (
        <p className="field-error">{error}</p>
      ) : (
        hint && <p className="field-hint">{hint}</p>
      )}
    </div>
  );
}
