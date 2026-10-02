import { ChevronRight, ExternalLink } from "lucide-react";
import { materialFileUrl } from "../../../api/materials";
import type { Material } from "../../../api/types";
import { formatDate } from "../../../lib/format";
import { IndexingStatusBadge } from "./IndexingStatusBadge";
import { MATERIAL_TYPES } from "./materialTypes";

interface MaterialRowProps {
  material: Material;
  courseId: number;
  onOpen: () => void;
}

export function MaterialRow({ material, courseId, onOpen }: MaterialRowProps) {
  const { label, icon: Icon, tone } = MATERIAL_TYPES[material.type];

  return (
    <div className="material-row">
      <button type="button" className="material-row-main" onClick={onOpen}>
        <span className={`icon-tile tone-${tone}`}>
          <Icon size={20} />
        </span>
        <span className="material-row-text">
          <span className="material-title">{material.title}</span>
          <span className="material-meta">
            {label} · Added {formatDate(material.created_at)}
          </span>
        </span>
      </button>

      {material.tags.length > 0 && (
        <div className="material-tags">
          {material.tags.map((tag) => (
            <span key={tag} className="chip">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="material-row-side">
        <IndexingStatusBadge material={material} courseId={courseId} />
        {material.type === "pdf" && (
          // PDFs open in a new browser tab.
          <a
            className="btn btn-ghost btn-sm btn-icon"
            href={materialFileUrl(material.id)}
            target="_blank"
            rel="noreferrer"
            aria-label={`Open ${material.title} in a new tab`}
            title="Open in a new tab"
          >
            <ExternalLink size={16} />
          </a>
        )}
        <ChevronRight size={18} className="material-row-chevron" aria-hidden="true" />
      </div>
    </div>
  );
}
