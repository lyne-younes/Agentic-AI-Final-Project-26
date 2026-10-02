import { Search } from "lucide-react";
import { Link } from "react-router";
import { EmptyState } from "../components/ui/EmptyState";

export function NotFoundPage() {
  return (
    <EmptyState
      icon={<Search size={30} />}
      tone="slate"
      title="Page not found"
      description="The page you're looking for doesn't exist or has moved."
      actions={
        <Link to="/courses" className="btn btn-primary">
          Back to My Library
        </Link>
      }
    />
  );
}
