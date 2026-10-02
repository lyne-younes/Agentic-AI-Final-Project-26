import { ExternalLink, LoaderCircle, Pencil, Trash } from "lucide-react";
import { useId, useState, type FormEvent } from "react";
import {
  materialFileUrl,
  useDeleteMaterial,
  useMaterial,
  useUpdateMaterial,
} from "../../../api/materials";
import type { MaterialDetail } from "../../../api/types";
import { Button } from "../../../components/ui/Button";
import { ConfirmDialog } from "../../../components/ui/ConfirmDialog";
import { Field } from "../../../components/ui/Field";
import { Modal } from "../../../components/ui/Modal";
import { TagInput } from "../../../components/ui/TagInput";
import { formatDate } from "../../../lib/format";
import { IndexingStatusBadge } from "./IndexingStatusBadge";
import { MATERIAL_TYPES } from "./materialTypes";

interface MaterialDrawerProps {
  courseId: number;
  materialId: number | null;
  onClose: () => void;
  tagSuggestions: string[];
}

/** In-app viewing: notes and extracted text render inline; files can open in a tab. */
export function MaterialDrawer({ courseId, materialId, onClose, tagSuggestions }: MaterialDrawerProps) {
  const { data: material, error } = useMaterial(materialId);

  return (
    <Modal
      open={materialId !== null}
      onClose={onClose}
      variant="drawer"
      size="lg"
      title={material?.title ?? "Loading…"}
      description={
        material
          ? `${MATERIAL_TYPES[material.type].label} · Added ${formatDate(material.created_at)}`
          : undefined
      }
    >
      {error ? (
        <p className="form-error" role="alert">
          {error.message}
        </p>
      ) : material ? (
        <MaterialDetails
          key={material.id}
          courseId={courseId}
          material={material}
          onDeleted={onClose}
          tagSuggestions={tagSuggestions}
        />
      ) : (
        <div className="drawer-loading">
          <LoaderCircle size={24} className="spin" />
        </div>
      )}
    </Modal>
  );
}

interface MaterialDetailsProps {
  courseId: number;
  material: MaterialDetail;
  onDeleted: () => void;
  tagSuggestions: string[];
}

function MaterialDetails({ courseId, material, onDeleted, tagSuggestions }: MaterialDetailsProps) {
  const id = useId();
  const update = useUpdateMaterial(courseId, material.id);
  const remove = useDeleteMaterial(courseId);
  const [tags, setTags] = useState(material.tags);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(material.title);
  const [content, setContent] = useState(material.raw_text);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const isNote = material.type === "authored_note";
  const tagsChanged = tags.join("\n") !== material.tags.join("\n");

  function startEditing() {
    setTitle(material.title);
    setContent(material.raw_text);
    update.reset();
    setEditing(true);
  }

  function saveEdits(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) return;
    // Only in-app notes have editable content; uploaded files can only be renamed.
    const changes = isNote ? { title: title.trim(), content } : { title: title.trim() };
    update.mutate(changes, { onSuccess: () => setEditing(false) });
  }

  return (
    <div className="material-details">
      <section className="drawer-section">
        <div className="drawer-row">
          <IndexingStatusBadge material={material} courseId={courseId} />
          {!isNote && (
            <a
              className="btn btn-secondary btn-sm"
              href={materialFileUrl(material.id)}
              target="_blank"
              rel="noreferrer"
            >
              <ExternalLink size={14} />
              {material.type === "pdf" ? "Open PDF" : "Open original file"}
            </a>
          )}
          {!editing && (
            <Button size="sm" onClick={startEditing}>
              <Pencil size={14} />
              {isNote ? "Edit note" : "Rename"}
            </Button>
          )}
        </div>
      </section>

      <section className="drawer-section">
        <h3>
          <label htmlFor={`${id}-tags`}>Tags</label>
        </h3>
        <TagInput id={`${id}-tags`} value={tags} onChange={setTags} suggestions={tagSuggestions} />
        {tagsChanged && (
          <div className="drawer-row">
            <Button
              size="sm"
              variant="primary"
              loading={update.isPending}
              onClick={() => update.mutate({ tags }, { onSuccess: (saved) => setTags(saved.tags) })}
            >
              Save tags
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setTags(material.tags)}>
              Discard
            </Button>
          </div>
        )}
        {!editing && update.error && (
          <p className="form-error" role="alert">
            {update.error.message}
          </p>
        )}
      </section>

      {editing ? (
        <form className="form drawer-section" onSubmit={saveEdits} noValidate>
          <Field
            label="Title"
            htmlFor={`${id}-title`}
            required
            error={title.trim() ? null : "The title can't be empty."}
          >
            <input
              id={`${id}-title`}
              className="input"
              value={title}
              maxLength={200}
              aria-invalid={!title.trim()}
              onChange={(event) => setTitle(event.target.value)}
            />
          </Field>
          {isNote && (
            <Field label="Note" htmlFor={`${id}-content`}>
              <textarea
                id={`${id}-content`}
                className="textarea note-textarea"
                value={content}
                onChange={(event) => setContent(event.target.value)}
              />
            </Field>
          )}
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
        <section className="drawer-section">
          <h3>{isNote ? "Note" : "Extracted text"}</h3>
          {!isNote && (
            <p className="field-hint">This is the text the assistant reads from the file.</p>
          )}
          {material.raw_text ? (
            <div className="material-text">{material.raw_text}</div>
          ) : (
            <p className="text-subtle">This note is empty.</p>
          )}
        </section>
      )}

      <section className="drawer-section">
        <Button variant="ghost" className="danger-action" onClick={() => setConfirmingDelete(true)}>
          <Trash size={16} />
          Delete material
        </Button>
      </section>

      <ConfirmDialog
        open={confirmingDelete}
        title="Delete this material?"
        message={`"${material.title}" will be removed from the course, and the assistant will stop using it.`}
        confirmLabel="Delete"
        loading={remove.isPending}
        error={remove.error?.message}
        onClose={() => setConfirmingDelete(false)}
        onConfirm={() =>
          remove.mutate(material.id, {
            onSuccess: () => {
              setConfirmingDelete(false);
              onDeleted();
            },
          })
        }
      />
    </div>
  );
}
