import { Plus } from "lucide-react";
import { Link, NavLink } from "react-router";
import type { ChatSession } from "../../../api/types";
import { formatRelative } from "../../../lib/format";

interface ChatSessionListProps {
  /** Where chats live: `/courses/3/chat` for a course, `/planner` for the global planner. */
  basePath: string;
  sessions: ChatSession[];
  loading: boolean;
  emptyHint?: string;
  newLabel?: string;
}

export function ChatSessionList({
  basePath,
  sessions,
  loading,
  emptyHint = "Your chats will appear here.",
  newLabel = "New chat",
}: ChatSessionListProps) {
  return (
    <nav className="chat-sessions" aria-label="Chats">
      <div className="chat-sessions-header">
        <h2 className="chat-sessions-heading">History</h2>
        <Link to={basePath} className="btn btn-sm btn-secondary">
          <Plus size={15} />
          {newLabel}
        </Link>
      </div>

      {loading ? (
        <div className="chat-sessions-skeleton" aria-busy="true">
          {[0, 1, 2].map((index) => (
            <div key={index} className="skeleton" style={{ height: 44 }} />
          ))}
        </div>
      ) : sessions.length === 0 ? (
        <p className="chat-sessions-empty">{emptyHint}</p>
      ) : (
        <ul>
          {sessions.map((session) => (
            <li key={session.id}>
              <NavLink
                to={`${basePath}/${session.id}`}
                className="chat-session-link"
                title={session.title}
              >
                <span className="truncate">{session.title}</span>
                <span className="chat-session-time">
                  {formatRelative(session.last_message_at ?? session.created_at)}
                </span>
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </nav>
  );
}
