import { FolderOpen, NotebookPen, Tag, Upload } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { useOutletContext, useSearchParams } from "react-router";
import { useMaterials } from "../../../api/materials";
import type { Course, Material } from "../../../api/types";
import { Button } from "../../../components/ui/Button";
import { EmptyState } from "../../../components/ui/EmptyState";
import { ErrorState } from "../../../components/ui/ErrorState";
import { pluralize } from "../../../lib/format";
import { MaterialDrawer } from "./MaterialDrawer";
import { MaterialRow } from "./MaterialRow";
import "./materials.css";
import { NoteModal } from "./NoteModal";
import { UploadMaterialModal } from "./UploadMaterialModal";

function collectTags(materials: Material[]): string[] {
  const byLowercase = new Map<string, string>();
  for (const material of materials) {
    for (const tag of material.tags) {
      if (!byLowercase.has(tag.toLowerCase())) byLowercase.set(tag.toLowerCase(), tag);
    }
  }
  return [...byLowercase.values()].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
}

export function MaterialsPage() {
  const course = useOutletContext<Course>();
  const { data: materials, isPending, error, refetch } = useMaterials(course.id);
  const [searchParams, setSearchParams] = useSearchParams();
  const [dialog, setDialog] = useState<"upload" | "note" | null>(null);
  const [openMaterialId, setOpenMaterialId] = useState<number | null>(null);

  const activeTag = searchParams.get("tag");
  const allTags = useMemo(() => collectTags(materials ?? []), [materials]);
  const visibleMaterials = activeTag
    ? (materials ?? []).filter((material) =>
        material.tags.some((tag) => tag.toLowerCase() === activeTag.toLowerCase()),
      )
    : (materials ?? []);

  // The tag filter lives in the URL so a filtered view can be bookmarked or shared.
  function selectTag(tag: string | null) {
    setSearchParams(tag ? { tag } : {}, { replace: true });
  }

  const uploadButton = (
    <Button variant="primary" onClick={() => setDialog("upload")}>
      <Upload size={16} />
      Upload file
    </Button>
  );
  const noteButton = (
    <Button onClick={() => setDialog("note")}>
      <NotebookPen size={16} />
      New note
    </Button>
  );

  let content: ReactNode;
  if (isPending) {
    content = <MaterialListSkeleton />;
  } else if (error) {
    content = <ErrorState message={error.message} onRetry={() => void refetch()} />;
  } else if (materials.length === 0) {
    content = (
      <EmptyState
        icon={<FolderOpen size={32} />}
        tone="teal"
        title="No materials yet"
        description="Upload PDFs, Word documents or text files, or write a note. Everything you add is indexed so the assistant can find it."
        actions={
          <>
            {uploadButton}
            {noteButton}
          </>
        }
      />
    );
  } else if (visibleMaterials.length === 0) {
    content = (
      <div className="filter-empty">
        <p>No materials are tagged “{activeTag}”.</p>
        <Button variant="ghost" onClick={() => selectTag(null)}>
          Show all materials
        </Button>
      </div>
    );
  } else {
    content = (
      <ul className="material-list">
        {visibleMaterials.map((material) => (
          <li key={material.id}>
            <MaterialRow
              material={material}
              courseId={course.id}
              onOpen={() => setOpenMaterialId(material.id)}
            />
          </li>
        ))}
      </ul>
    );
  }

  return (
    <section className="materials" aria-labelledby="materials-heading">
      <div className="section-header">
        <div>
          <h2 id="materials-heading" className="section-title">
            Materials
          </h2>
          <p className="text-muted">
            {materials && materials.length > 0
              ? `${pluralize(materials.length, "item")} the assistant can draw on for this course.`
              : "Everything the assistant can draw on for this course."}
          </p>
        </div>
        {materials && materials.length > 0 && (
          <div className="section-actions">
            {noteButton}
            {uploadButton}
          </div>
        )}
      </div>

      {allTags.length > 0 && (
        <div className="tag-filter" role="group" aria-label="Filter by tag">
          <button
            type="button"
            className="chip-filter"
            aria-pressed={!activeTag}
            onClick={() => selectTag(null)}
          >
            All
          </button>
          {allTags.map((tag) => {
            const selected = activeTag?.toLowerCase() === tag.toLowerCase();
            return (
              <button
                key={tag}
                type="button"
                className="chip-filter"
                aria-pressed={selected}
                onClick={() => selectTag(selected ? null : tag)}
              >
                <Tag size={12} />
                {tag}
              </button>
            );
          })}
        </div>
      )}

      {content}

      <UploadMaterialModal
        open={dialog === "upload"}
        onClose={() => setDialog(null)}
        courseId={course.id}
        tagSuggestions={allTags}
      />
      <NoteModal
        open={dialog === "note"}
        onClose={() => setDialog(null)}
        courseId={course.id}
        tagSuggestions={allTags}
      />
      <MaterialDrawer
        courseId={course.id}
        materialId={openMaterialId}
        onClose={() => setOpenMaterialId(null)}
        tagSuggestions={allTags}
      />
    </section>
  );
}

function MaterialListSkeleton() {
  return (
    <ul className="material-list" aria-busy="true" aria-label="Loading materials">
      {[0, 1, 2].map((index) => (
        <li key={index} className="material-row">
          <div className="skeleton" style={{ width: 40, height: 40, borderRadius: 10 }} />
          <div style={{ display: "grid", gap: 6, flex: 1 }}>
            <div className="skeleton" style={{ height: 16, width: "40%" }} />
            <div className="skeleton" style={{ height: 12, width: "25%" }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
