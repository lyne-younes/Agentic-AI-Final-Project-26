import { ArrowUp } from "lucide-react";
import { useEffect, useRef, type KeyboardEvent } from "react";
import { Button } from "../../../components/ui/Button";

// Matches MessageCreate in backend/app/chat/schemas.py.
const MAX_LENGTH = 4000;
const MAX_HEIGHT_PX = 200;

const INPUT_ID = "chat-input";

/** Focus the composer with the caret at the end, e.g. after a suggestion pre-fills it. */
export function focusChatInput() {
  // After React has rendered the new value.
  requestAnimationFrame(() => {
    const input = document.getElementById(INPUT_ID) as HTMLTextAreaElement | null;
    input?.focus();
    input?.setSelectionRange(input.value.length, input.value.length);
  });
}

interface ChatComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  busy: boolean;
  placeholder: string;
}

export function ChatComposer({ value, onChange, onSend, busy, placeholder }: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const canSend = value.trim().length > 0 && !busy;

  // Grow with the text, up to a limit, then scroll inside.
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [value]);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      if (canSend) onSend();
    }
  }

  return (
    <form
      className="chat-composer"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSend) onSend();
      }}
    >
      <label htmlFor={INPUT_ID} className="visually-hidden">
        Message
      </label>
      <textarea
        ref={textareaRef}
        id={INPUT_ID}
        rows={1}
        value={value}
        maxLength={MAX_LENGTH}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <Button
        type="submit"
        variant="accent"
        iconOnly
        className="chat-send"
        aria-label="Send message"
        disabled={!canSend}
      >
        <ArrowUp size={18} />
      </Button>
      <p className="chat-composer-hint">Enter to send · Shift + Enter for a new line</p>
    </form>
  );
}
