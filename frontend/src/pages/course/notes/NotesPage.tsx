import { ChevronLeft, ChevronRight, History, NotepadText, Pencil, Undo2 } from "lucide-react";
import { useState } from "react";
import { useOutletContext, useSearchParams } from "react-router";
import { ApiError } from "../../../api/client";
import { useSummary, useSummaryHistory, useUpdateSummary } from "../../../api/summaries";
import type { Course } from "../../../api/types";
import { Markdown } from "../../../components/Markdown";
import { Button } from "../../../components/ui/Button";
import { EmptyState } from "../../../components/ui/EmptyState";
import { ErrorState } from "../../../components/ui/ErrorState";
import "./notes.css";

const longDate = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

interface Version {
  number: number;
  content: string;
  date: string; // current: last updated; archived: when it was replaced
  current: boolean;
}

/**
 * The course summary and its versions. The version is in the URL (`?version=2`); without it the
 * current, editable version is shown.
 */
export function NotesPage() {
  const course = useOutletContext<Course>();
  const summary = useSummary(course.id);
  const history = useSummaryHistory(course.id);
  const update = useUpdateSummary(course.id);
  const [searchParams, setSearchParams] = useSearchParams();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  const notFound = summary.error instanceof ApiError && summary.error.status === 404;

  if (notFound) {
    return (
      <EmptyState
        icon={<NotepadText size={30} />}
        tone="amber"
        title="No summary yet"
        description={`Ask the assistant to summarize ${course.name} from the Chat tab, or use the Summarize button there.`}
      />
    );
  }
  if (summary.error) {
    return <ErrorState message={summary.error.message} onRetry={() => void summary.refetch()} />;
  }
  if (!summary.data) {
    return <div className="skeleton" style={{ height: 200 }} />;
  }

  const data = summary.data;
  // Newest first: the current summary, then the archived versions (already newest first).
  const archived = history.data ?? [];
  const currentNumber = Math.max(0, ...archived.map((v) => v.version_number)) + 1;
  const versions: Version[] = [
    { number: currentNumber, content: data.content, date: data.updated_at, current: true },
    ...archived.map((v) => ({
      number: v.version_number,
      content: v.content,
      date: v.archived_at,
      current: false,
    })),
  ];

  const requested = Number(searchParams.get("version"));
  const index = Math.max(
    0,
    versions.findIndex((v) => v.number === requested),
  );
  const shown = versions[index];
  const older = versions[index + 1];
  const newer = versions[index - 1];

  function showVersion(version: Version) {
    setSearchParams(
      (params) => {
        if (version.current) params.delete("version");
        else params.set("version", String(version.number));
        return params;
      },
      { preventScrollReset: true },
    );
  }

  function startEditing() {
    setDraft(data.content);
    update.reset();
    setEditing(true);
  }

  function save() {
    if (!draft.trim()) return;
    update.mutate(draft, { onSuccess: () => setEditing(false) });
  }

  return (
    <div className="page notes-page">
      <div className="version-bar" role="toolbar" aria-label="Summary versions">
        <div className="version-picker">
          <History size={16} className="version-icon" aria-hidden="true" />
          <label htmlFor="version-select" className="visually-hidden">
            Version
          </label>
          <select
            id="version-select"
            className="version-select"
            value={shown.number}
            disabled={editing || versions.length === 1}
            onChange={(event) => {
              const next = versions.find((v) => v.number === Number(event.target.value));
              if (next) showVersion(next);
            }}
          >
            {versions.map((version) => (
              <option key={version.number} value={version.number}>
                Version {version.number}
                {version.current ? " · Current" : ""}
              </option>
            ))}
          </select>
          <div className="version-steps">
            <Button
              size="sm"
              variant="ghost"
              iconOnly
              aria-label="Older version"
              title="Older version"
              disabled={editing || !older}
              onClick={() => older && showVersion(older)}
            >
              <ChevronLeft size={16} />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              iconOnly
              aria-label="Newer version"
              title="Newer version"
              disabled={editing || !newer}
              onClick={() => newer && showVersion(newer)}
            >
              <ChevronRight size={16} />
            </Button>
          </div>
        </div>

        <p className="version-meta">
          <span className="version-position">
            {versions.length === 1 ? "Only version" : `${index + 1} of ${versions.length}`}
          </span>
          <span aria-hidden="true">·</span>
          <span>
            {shown.current ? "Updated" : "Replaced"} {longDate.format(new Date(shown.date))}
          </span>
          {shown.current && data.is_edited && <span className="badge">Edited by you</span>}
          {!shown.current && <span className="badge">Read-only</span>}
        </p>

        <div className="version-actions">
          {shown.current ? (
            !editing && (
              <Button size="sm" onClick={startEditing}>
                <Pencil size={14} />
                Edit
              </Button>
            )
          ) : (
            <Button size="sm" variant="accent" onClick={() => showVersion(versions[0])}>
              <Undo2 size={14} />
              Back to current
            </Button>
          )}
        </div>
      </div>

      {!shown.current && (
        <p className="version-notice" role="status">
          You're reading version {shown.number}, an earlier summary that was replaced on{" "}
          {longDate.format(new Date(shown.date))}. The current version is {versions[0].number}.
        </p>
      )}

      <article className={`notes-document${shown.current ? "" : " notes-document-archived"}`}>
        {editing && shown.current ? (
          <form
            className="form"
            onSubmit={(event) => {
              event.preventDefault();
              save();
            }}
          >
            <label htmlFor="summary-editor" className="visually-hidden">
              Summary
            </label>
            <textarea
              id="summary-editor"
              className="textarea summary-textarea"
              value={draft}
              autoFocus
              onChange={(event) => setDraft(event.target.value)}
            />
            {update.error && (
              <p className="form-error" role="alert">
                {update.error.message}
              </p>
            )}
            <div className="modal-actions">
              <Button onClick={() => setEditing(false)}>Cancel</Button>
              <Button type="submit" variant="primary" loading={update.isPending}>
                Save
              </Button>
            </div>
          </form>
        ) : (
          <Markdown>{shown.content}</Markdown>
        )}
      </article>
    </div>
  );
}
