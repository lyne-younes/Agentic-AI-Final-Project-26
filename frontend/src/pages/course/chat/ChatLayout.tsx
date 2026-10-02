import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useId, useState, type ReactNode } from "react";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { useMediaQuery } from "../../../lib/useMediaQuery";

// Whether the student collapsed the history column (per browser).
const HIDDEN_KEY = "chat-history-hidden";

function readHidden(): boolean {
  try {
    return localStorage.getItem(HIDDEN_KEY) === "true";
  } catch {
    return false;
  }
}

function writeHidden(hidden: boolean) {
  try {
    localStorage.setItem(HIDDEN_KEY, String(hidden));
  } catch {
    // Not remembered; the toggle still works for this visit.
  }
}

interface ChatLayoutProps {
  label: string;
  className?: string;
  /** The chat history (a ChatSessionList): a collapsible column when wide, a drawer below 1024px. */
  history: ReactNode;
  children: ReactNode;
}

/** Shared frame for the course chat and the planner: history beside (or over) the conversation. */
export function ChatLayout({ label, className, history, children }: ChatLayoutProps) {
  const wide = useMediaQuery("(min-width: 1024px)");
  const [hidden, setHidden] = useState(readHidden); // wide screens: column collapsed
  const [drawerOpen, setDrawerOpen] = useState(false); // narrow screens: drawer open
  const historyId = useId();

  function toggle() {
    if (!wide) {
      setDrawerOpen(true);
      return;
    }
    setHidden(!hidden);
    writeHidden(!hidden);
  }

  const collapsed = wide && hidden;
  const showing = wide && !hidden;
  const classes = ["chat-layout", collapsed && "chat-layout-history-hidden", className]
    .filter(Boolean)
    .join(" ");

  return (
    <section className={classes} aria-label={label}>
      {wide && (
        // Kept in the DOM while collapsed so it can animate; `inert` hides it from focus.
        <aside id={historyId} className="chat-history" inert={collapsed}>
          {history}
        </aside>
      )}
      <div className="chat-panel">
        <div className="chat-panel-toolbar">
          <Button
            size="sm"
            variant="ghost"
            onClick={toggle}
            aria-expanded={wide ? showing : drawerOpen}
            aria-controls={wide ? historyId : undefined}
          >
            {showing ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
            {showing ? "Hide history" : "Show history"}
          </Button>
        </div>
        {children}
      </div>
      {!wide && (
        <Modal
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          title="Chat history"
          variant="drawer"
          side="left"
          size="sm"
        >
          {/* Picking a chat or "New chat" closes the drawer, even when the URL doesn't change. */}
          <div
            onClick={(event) => {
              if ((event.target as HTMLElement).closest("a")) setDrawerOpen(false);
            }}
          >
            {history}
          </div>
        </Modal>
      )}
    </section>
  );
}
