"use client";

import { usePathname } from "next/navigation";
import { useHealth } from "@/hooks/use-health";
import { useSessions } from "@/hooks/use-sessions";
import { truncateId } from "@/lib/utils";

export function Header() {
  const { health } = useHealth();
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
  } else if (pathname === "/settings") {
    pageTitle = "Settings";
  }

  return (
    <header className="h-12 border-b border-[var(--border)] flex items-center justify-between px-4">
      <h2 className="text-sm font-medium truncate">{pageTitle}</h2>
      <div className="flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
        <span
          className={`w-2 h-2 rounded-full ${health ? "bg-green-500" : "bg-red-500"}`}
        />
        {health ? "Backend connected" : "Backend offline"}
      </div>
    </header>
  );
}
