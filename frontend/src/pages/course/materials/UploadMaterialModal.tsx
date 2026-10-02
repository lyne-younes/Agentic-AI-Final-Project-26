import { CloudUpload, FileText, X } from "lucide-react";
import { useId, useRef, useState, type FormEvent } from "react";
import { useUploadMaterial } from "../../../api/materials";
import { Button } from "../../../components/ui/Button";
import { Field } from "../../../components/ui/Field";
import { Modal } from "../../../components/ui/Modal";
import { TagInput } from "../../../components/ui/TagInput";
import { fileStem, formatBytes } from "../../../lib/format";

// Mirrors the backend's accepted types and size limit (backend/app/materials).
const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md"];
const MAX_BYTES = 25 * 1024 * 1024;

interface UploadMaterialModalProps {
  open: boolean;
  onClose: () => void;
  courseId: number;
  tagSuggestions: string[];
}

export function UploadMaterialModal({ open, onClose, courseId, tagSuggestions }: UploadMaterialModalProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Upload a file"
      description="PDF, Word (.docx) or text (.txt, .md), up to 25 MB."
    >
      <UploadForm courseId={courseId} onDone={onClose} tagSuggestions={tagSuggestions} />
    </Modal>
  );
}

function UploadForm({
  courseId,
  onDone,
  tagSuggestions,
}: {
  courseId: number;
  onDone: () => void;
  tagSuggestions: string[];
}) {
  const id = useId();
  const upload = useUploadMaterial(courseId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  function chooseFile(candidate: File | undefined) {
    if (!candidate) return;
    const extension = candidate.name.slice(candidate.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setFileError("Choose a PDF, Word (.docx), .txt or .md file.");
    } else if (candidate.size > MAX_BYTES) {
      setFileError("Files must be 25 MB or smaller.");
    } else {
      setFileError(null);
      setFile(candidate);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setFileError("Choose a file to upload.");
      return;
    }
    upload.mutate({ file, title, tags }, { onSuccess: onDone });
  }

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      {file ? (
        <div className="file-chip">
          <span className="icon-tile tone-teal">
            <FileText size={20} />
          </span>
          <div className="file-chip-text">
            <strong className="truncate">{file.name}</strong>
            <span className="text-subtle">{formatBytes(file.size)}</span>
          </div>
          <Button variant="ghost" iconOnly aria-label="Remove file" onClick={() => setFile(null)}>
            <X size={16} />
          </Button>
        </div>
      ) : (
        <div
          className={`dropzone${dragging ? " dropzone-active" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            chooseFile(event.dataTransfer.files[0]);
          }}
        >
          <CloudUpload size={30} />
          <p>
            <strong>Drag a file here</strong> or
          </p>
          <Button data-autofocus onClick={() => inputRef.current?.click()}>
            Browse files
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS.join(",")}
            hidden
            onChange={(event) => {
              chooseFile(event.target.files?.[0]);
              event.target.value = ""; // allow choosing the same file again after removing it
            }}
          />
        </div>
      )}
      {fileError && <p className="field-error">{fileError}</p>}

      <Field label="Title" htmlFor={`${id}-title`} hint="Defaults to the file name.">
        <input
          id={`${id}-title`}
          className="input"
          value={title}
          maxLength={200}
          placeholder={file ? fileStem(file.name) : "e.g. Lecture 3 slides"}
          onChange={(event) => setTitle(event.target.value)}
        />
      </Field>

      <Field
        label="Tags"
        htmlFor={`${id}-tags`}
        hint="Optional. Tags let you point the assistant at specific material later."
      >
        <TagInput id={`${id}-tags`} value={tags} onChange={setTags} suggestions={tagSuggestions} />
      </Field>

      {upload.error && (
        <p className="form-error" role="alert">
          {upload.error.message}
        </p>
      )}

      <div className="modal-actions">
        <Button onClick={onDone}>Cancel</Button>
        <Button type="submit" variant="primary" loading={upload.isPending}>
          Upload
        </Button>
      </div>
    </form>
  );
}
