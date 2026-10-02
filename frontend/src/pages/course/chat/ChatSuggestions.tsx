import type { ReactNode } from "react";

export interface Suggestion {
  label: string;
  icon?: ReactNode;
  /** Sent as a message straight away (the action buttons)... */
  prompt?: string;
  /** ...or handled locally, e.g. pre-filling the input. */
  onPick?: () => void;
}

interface ChatSuggestionsProps {
  suggestions: Suggestion[];
  disabled: boolean;
  onSend: (prompt: string) => void;
  children?: ReactNode; // anything else for the row, placed at its end
}

/** A row of chips above the composer. */
export function ChatSuggestions({ suggestions, disabled, onSend, children }: ChatSuggestionsProps) {
  return (
    <div className="chat-suggestions" role="group" aria-label="Suggestions">
      {suggestions.map((suggestion) => (
        <button
          key={suggestion.label}
          type="button"
          className="chat-chip"
          disabled={disabled}
          onClick={() => {
            if (suggestion.prompt) onSend(suggestion.prompt);
            else suggestion.onPick?.();
          }}
        >
          {suggestion.icon}
          {suggestion.label}
        </button>
      ))}
      {children}
    </div>
  );
}
