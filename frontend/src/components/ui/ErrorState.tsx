import { RefreshCw, TriangleAlert } from "lucide-react";
import { Button } from "./Button";

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="error-state" role="alert">
      <span className="icon-tile tone-rose">
        <TriangleAlert size={20} />
      </span>
      <p>{message}</p>
      {onRetry && (
        <Button onClick={onRetry}>
          <RefreshCw size={16} />
          Try again
        </Button>
      )}
    </div>
  );
}
