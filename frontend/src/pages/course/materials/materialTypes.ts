import { File as FileIcon, FileText, FileType, NotebookPen, type LucideIcon } from "lucide-react";
import type { MaterialType } from "../../../api/types";
import type { Tone } from "../../../components/ui/EmptyState";

export const MATERIAL_TYPES: Record<MaterialType, { label: string; icon: LucideIcon; tone: Tone }> =
  {
    pdf: { label: "PDF", icon: FileText, tone: "rose" },
    docx: { label: "Word document", icon: FileType, tone: "sky" },
    text_file: { label: "Text file", icon: FileIcon, tone: "slate" },
    authored_note: { label: "Note", icon: NotebookPen, tone: "amber" },
  };
