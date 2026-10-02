import { useId, useState, type FormEvent } from "react";
import { useCreateNote } from "../../../api/materials";
import { Button } from "../../../components/ui/Button";
import { Field } from "../../../components/ui/Field";
import { Modal } from "../../../components/ui/Modal";
import { TagInput } from "../../../components/ui/TagInput";

interface NoteModalProps {
  open: boolean;
  onClose: () => void;
  courseId: number;
  tagSuggestions: string[];
}

export function NoteModal({ open, onClose, courseId, tagSuggestions }: NoteModalProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title="New note"
      description="Write directly in the app. Notes are indexed just like uploaded files."
    >
      <NoteForm courseId={courseId} onDone={onClose} tagSuggestions={tagSuggestions} />
    </Modal>
  );
}

type NoteErrors = Partial<Record<"title" | "content", string>>;

function NoteForm({
  courseId,
  onDone,
  tagSuggestions,
}: {
  courseId: number;
  onDone: () => void;
  tagSuggestions: string[];
}) {
  const id = useId();
  const createNote = useCreateNote(courseId);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [errors, setErrors] = useState<NoteErrors>({});

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors: NoteErrors = {};
    if (!title.trim()) nextErrors.title = "Give the note a title.";
    if (!content.trim()) nextErrors.content = "Write something first.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    createNote.mutate({ title: title.trim(), content, tags }, { onSuccess: onDone });
  }

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      <Field label="Title" htmlFor={`${id}-title`} required error={errors.title}>
        <input
          id={`${id}-title`}
          className="input"
          value={title}
          maxLength={200}
          placeholder="e.g. Week 3 lecture notes"
          aria-invalid={Boolean(errors.title)}
          data-autofocus
          onChange={(event) => setTitle(event.target.value)}
        />
      </Field>
      <Field label="Note" htmlFor={`${id}-content`} required error={errors.content}>
        <textarea
          id={`${id}-content`}
          className="textarea note-textarea"
          value={content}
          aria-invalid={Boolean(errors.content)}
          onChange={(event) => setContent(event.target.value)}
        />
      </Field>
      <Field label="Tags" htmlFor={`${id}-tags`} hint="Optional.">
        <TagInput id={`${id}-tags`} value={tags} onChange={setTags} suggestions={tagSuggestions} />
      </Field>

      {createNote.error && (
        <p className="form-error" role="alert">
          {createNote.error.message}
        </p>
      )}

      <div className="modal-actions">
        <Button onClick={onDone}>Cancel</Button>
        <Button type="submit" variant="primary" loading={createNote.isPending}>
          Save note
        </Button>
      </div>
    </form>
  );
}
