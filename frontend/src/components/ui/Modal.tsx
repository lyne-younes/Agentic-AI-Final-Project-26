import { X } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { Button } from "./Button";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  variant?: "dialog" | "drawer";
  size?: "sm" | "md" | "lg";
  side?: "left" | "right"; // drawers only
}

/**
 * Native <dialog> shown as a centred dialog or a drawer. Content only renders while open.
 * Put `data-autofocus` on the element that should receive focus when it opens.
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  variant = "dialog",
  size = "md",
  side = "right",
}: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const pressStartedOnBackdrop = useRef(false);
  const titleId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      dialog.querySelector<HTMLElement>("[data-autofocus]")?.focus();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      className={`modal modal-${variant} modal-${size}${variant === "drawer" && side === "left" ? " modal-drawer-left" : ""}`}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault(); // let the parent own the open state
        onClose();
      }}
      // Close on a backdrop click (where the press started, not a dragged text selection).
      onMouseDown={(event) => {
        pressStartedOnBackdrop.current = event.target === event.currentTarget;
      }}
      onClick={(event) => {
        if (pressStartedOnBackdrop.current && event.target === event.currentTarget) onClose();
      }}
    >
      {open && (
        <div className="modal-panel">
          <header className="modal-header">
            <div>
              <h2 id={titleId}>{title}</h2>
              {description && <p>{description}</p>}
            </div>
            <Button variant="ghost" iconOnly aria-label="Close" onClick={onClose}>
              <X size={18} />
            </Button>
          </header>
          <div className="modal-body">{children}</div>
          {footer && <footer className="modal-footer">{footer}</footer>}
        </div>
      )}
    </dialog>
  );
}
