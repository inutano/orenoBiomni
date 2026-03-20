"use client";

import { useRouter, usePathname } from "next/navigation";
import { MessageSquare, ListTodo, GitBranch, Wrench, Settings, Plus, Trash2 } from "lucide-react";
import { NavLink } from "./nav-link";
import { useSessions } from "@/hooks/use-sessions";
import { truncateId, relativeTime, cn } from "@/lib/utils";

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { sessions, isLoading, error, create, remove } = useSessions();

  const activeSessionId = pathname.startsWith("/chat/")
    ? pathname.split("/")[2]
    : null;

  async function handleNewChat() {
    const session = await create();
    router.push(`/chat/${session.id}`);
  }

  return (
    <aside className="w-64 border-r border-[var(--border)] flex flex-col h-full bg-[var(--muted)]">
      <div className="p-4 border-b border-[var(--border)]">
        <h1 className="text-lg font-bold">orenoBiomni</h1>
      </div>

      <div className="p-2">
        <button
          onClick={handleNewChat}
          aria-label="Start a new chat session"
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm bg-[var(--accent)] text-[var(--accent-foreground)] hover:opacity-80"
        >
          <Plus size={16} />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1" role="list" aria-label="Chat sessions">
        {isLoading && (
          <div className="space-y-2 px-3 py-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 rounded-lg bg-[var(--border)] animate-pulse" />
            ))}
          </div>
        )}
        {error && (
          <div className="px-3 py-2 text-xs text-[var(--destructive)]">
            {error}
          </div>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={cn(
              "group flex items-center gap-1 px-3 py-2 rounded-lg text-sm cursor-pointer hover:bg-[var(--background)] transition-colors",
              activeSessionId === s.id && "bg-[var(--background)] font-medium",
            )}
            onClick={() => router.push(`/chat/${s.id}`)}
          >
            <MessageSquare size={14} className="shrink-0 text-[var(--muted-foreground)]" />
            <span className="flex-1 truncate">
              {s.title || truncateId(s.id)}
            </span>
            <span className="text-xs text-[var(--muted-foreground)] group-hover:hidden">
              {relativeTime(s.updated_at)}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm("Delete this session?")) {
                  remove(s.id);
                }
              }}
              className="hidden group-hover:block text-[var(--muted-foreground)] hover:text-[var(--destructive)]"
              aria-label={`Delete session ${s.title || truncateId(s.id)}`}
              title="Delete session"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <nav className="p-2 border-t border-[var(--border)] space-y-1">
        <NavLink href="/runs" icon={<ListTodo size={16} />}>
          Runs
        </NavLink>
        <NavLink href="/pipelines" icon={<GitBranch size={16} />}>
          Pipelines
        </NavLink>
        <NavLink href="/tools" icon={<Wrench size={16} />}>
          Tools
        </NavLink>
        <NavLink href="/settings" icon={<Settings size={16} />}>
          Settings
        </NavLink>
      </nav>
    </aside>
  );
}
