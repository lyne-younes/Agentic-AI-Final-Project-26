import { CircleCheck, LoaderCircle, RefreshCw, TriangleAlert } from "lucide-react";
import { useReindexMaterial } from "../../../api/materials";
import type { Material } from "../../../api/types";
import { Button } from "../../../components/ui/Button";

/** Whether the assistant can search this material yet (the background chunk + embed job). */
export function IndexingStatusBadge({ material, courseId }: { material: Material; courseId: number }) {
  const reindex = useReindexMaterial(courseId);

  if (material.indexing_status === "pending") {
    return (
      <span className="badge" title="Preparing this material so the assistant can search it">
        <LoaderCircle size={12} className="spin" />
        Indexing
      </span>
    );
  }
  if (material.indexing_status === "indexed") {
    return (
      <span className="badge badge-teal" title="The assistant can use this material">
        <CircleCheck size={12} />
        Ready
      </span>
    );
  }
  return (
    <span className="indexing-failed">
      <span className="badge badge-danger" title="The assistant can't search this material yet">
        <TriangleAlert size={12} />
        Indexing failed
      </span>
      <Button
        size="sm"
        variant="ghost"
        loading={reindex.isPending}
        onClick={() => reindex.mutate(material.id)}
      >
        {!reindex.isPending && <RefreshCw size={14} />}
        Retry
      </Button>
    </span>
  );
}
