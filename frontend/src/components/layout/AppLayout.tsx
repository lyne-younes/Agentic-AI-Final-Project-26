import { Menu as MenuIcon, PanelLeftOpen } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router";
import { useMediaQuery } from "../../lib/useMediaQuery";
import { Button } from "../ui/Button";
import "./AppLayout.css";
import { Brand, Sidebar } from "./Sidebar";

// Whether the student hid the sidebar on a wide screen (per browser).
const HIDDEN_KEY = "sidebar-hidden";

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

export function AppLayout() {
  const narrow = useMediaQuery("(max-width: 767px)");
  const [sidebarOpen, setSidebarOpen] = useState(false); // narrow: the overlay is open
  const [sidebarHidden, setSidebarHidden] = useState(readHidden); // wide: the sidebar is hidden
  const { pathname } = useLocation();
  const sidebarRef = useRef<HTMLElement>(null);
  const showButtonRef = useRef<HTMLButtonElement>(null);

  // On small screens the sidebar is an overlay; close it after navigating.
  useEffect(() => setSidebarOpen(false), [pathname]);

  const setHidden = useCallback((hidden: boolean) => {
    // Don't strand keyboard focus inside a sidebar that is about to disappear.
    const focusInside = sidebarRef.current?.contains(document.activeElement) ?? false;
    setSidebarHidden(hidden);
    writeHidden(hidden);
    requestAnimationFrame(() => {
      if (hidden && focusInside) showButtonRef.current?.focus();
      if (!hidden) sidebarRef.current?.querySelector<HTMLElement>(".sidebar-hide")?.focus();
    });
  }, []);

  const hideSidebar = () => (narrow ? setSidebarOpen(false) : setHidden(true));
  const showSidebar = () => (narrow ? setSidebarOpen(true) : setHidden(false));

  // Ctrl/⌘ + B toggles the sidebar, like most editors.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (!(event.ctrlKey || event.metaKey) || event.shiftKey || event.altKey) return;
      if (event.key.toLowerCase() !== "b") return;
      event.preventDefault();
      if (narrow) setSidebarOpen((open) => !open);
      else setHidden(!sidebarHidden);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [narrow, sidebarHidden, setHidden]);

  const hidden = !narrow && sidebarHidden;
  const classes = ["app-shell", sidebarOpen && "sidebar-open", hidden && "sidebar-hidden"]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes}>
      <Sidebar ref={sidebarRef} onHide={hideSidebar} inert={hidden || (narrow && !sidebarOpen)} />
      <div className="sidebar-scrim" onClick={() => setSidebarOpen(false)} />
      <div className="app-content">
        {/* Shown on small screens, and on wide ones while the sidebar is hidden. */}
        <header className="app-topbar">
          <Button
            ref={showButtonRef}
            variant="ghost"
            iconOnly
            aria-label="Show sidebar"
            title="Show sidebar (Ctrl+B)"
            aria-expanded={narrow ? sidebarOpen : !sidebarHidden}
            onClick={showSidebar}
          >
            {narrow ? <MenuIcon size={20} /> : <PanelLeftOpen size={20} />}
          </Button>
          <Brand />
        </header>
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
