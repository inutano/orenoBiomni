"use client";

import { usePathname } from "next/navigation";
import { LogOut, Menu } from "lucide-react";
import { useHealth } from "@/hooks/use-health";
import { useAuth } from "@/hooks/use-auth";
import { useSessions } from "@/hooks/use-sessions";
import { truncateId } from "@/lib/utils";

interface HeaderProps {
  onMenuToggle?: () => void;
}

export function Header({ onMenuToggle }: HeaderProps) {
  const { health } = useHealth();
  const { user, isAuthenticated, providers, logout } = useAuth();
  const pathname = usePathname();
  const { sessions } = useSessions();

  let pageTitle = "";
  if (pathname.startsWith("/chat/")) {
    const sessionId = pathname.split("/")[2];
    const session = sessions.find((s) => s.id === sessionId);
    pageTitle = session?.title || truncateId(sessionId);
  } else if (pathname === "/runs") {
    pageTitle = "Workflow Runs";
  } else if (pathname.startsWith("/runs/")) {
    pageTitle = "Run Details";
  } else if (pathname === "/pipelines") {
    pageTitle = "Pipelines";
  } else if (pathname === "/tools") {
    pageTitle = "Tools & Datasets";
  } else if (pathname === "/settings") {
    pageTitle = "Settings";
  }

  return (
    <header className="h-12 border-b border-[var(--border)] flex items-center justify-between px-4">
      <div className="flex items-center gap-2">
        {onMenuToggle && (
          <button
            onClick={onMenuToggle}
            className="md:hidden p-2 -ml-1 rounded hover:bg-[var(--muted)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
            aria-label="Toggle sidebar menu"
          >
            <Menu size={20} />
          </button>
        )}
        <h2 className="text-sm font-medium truncate">
          {pageTitle || <span className="md:hidden">orenoBiomni</span>}
        </h2>
      </div>
      <div className="flex items-center gap-3">
        {isAuthenticated && providers?.auth_enabled && user && (
          <div className="flex items-center gap-2 text-xs">
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.display_name || user.email}
                className="w-6 h-6 rounded-full"
              />
            ) : (
              <span className="w-6 h-6 rounded-full bg-[var(--accent)] flex items-center justify-center text-[var(--accent-foreground)] text-xs font-medium">
                {(user.display_name || user.email).charAt(0).toUpperCase()}
              </span>
            )}
            <span className="text-[var(--foreground)] max-w-[120px] truncate">
              {user.display_name || user.email}
            </span>
            <button
              onClick={logout}
              className="p-1 rounded hover:bg-[var(--muted)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut size={14} />
            </button>
          </div>
        )}
        <div className="flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
          <span
            className={`w-2 h-2 rounded-full ${health ? "bg-green-500" : "bg-red-500"}`}
          />
          <span className="hidden sm:inline">{health ? "Backend connected" : "Backend offline"}</span>
        </div>
      </div>
    </header>
  );
}
