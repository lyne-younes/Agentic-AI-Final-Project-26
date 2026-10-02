import { X } from "lucide-react";
import { useId, useState } from "react";

// Matches the backend's normalize_tags rules (backend/app/materials/schemas.py).
const MAX_TAG_LENGTH = 40;

interface TagInputProps {
  id: string;
  value: string[];
  onChange: (tags: string[]) => void;
  suggestions?: string[];
}

/** Free-form tags: type and press Enter or comma to add; Backspace on an empty field removes the last. */
export function TagInput({ id, value, onChange, suggestions = [] }: TagInputProps) {
  const [draft, setDraft] = useState("");
  const listId = useId();

  function commit(raw: string) {
    const tag = raw.split(/\s+/).filter(Boolean).join(" ").slice(0, MAX_TAG_LENGTH);
    setDraft("");
    if (!tag || value.some((existing) => existing.toLowerCase() === tag.toLowerCase())) return;
    onChange([...value, tag]);
  }

  const unusedSuggestions = suggestions.filter(
    (suggestion) => !value.some((tag) => tag.toLowerCase() === suggestion.toLowerCase()),
  );

  return (
    <div className="tag-input">
      {value.map((tag) => (
        <span key={tag} className="chip">
          {tag}
          <button
            type="button"
            aria-label={`Remove tag ${tag}`}
            onClick={() => onChange(value.filter((existing) => existing !== tag))}
          >
            <X size={12} />
          </button>
        </span>
      ))}
      <input
        id={id}
        value={draft}
        list={unusedSuggestions.length > 0 ? listId : undefined}
        placeholder={value.length === 0 ? "e.g. week3, exam1" : ""}
        onChange={(event) => {
          const next = event.target.value;
          if (next.endsWith(",")) commit(next.slice(0, -1));
          else setDraft(next);
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            commit(draft);
          } else if (event.key === "Backspace" && draft === "" && value.length > 0) {
            onChange(value.slice(0, -1));
          }
        }}
        onBlur={() => {
          if (draft) commit(draft);
        }}
      />
      {unusedSuggestions.length > 0 && (
        <datalist id={listId}>
          {unusedSuggestions.map((suggestion) => (
            <option key={suggestion} value={suggestion} />
          ))}
        </datalist>
      )}
    </div>
  );
}
