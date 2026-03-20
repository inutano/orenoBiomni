"use client";

import { useRouter } from "next/navigation";
import { useSessions } from "@/hooks/use-sessions";
import { useEffect } from "react";

export default function HomePage() {
  const router = useRouter();
  const { sessions, isLoading, create } = useSessions();

  useEffect(() => {
    if (isLoading) return;
    if (sessions.length > 0) {
      router.replace(`/chat/${sessions[0].id}`);
    } else {
      create().then((s) => router.replace(`/chat/${s.id}`));
    }
  }, [isLoading, sessions, router, create]);

  return (
    <div className="flex items-center justify-center h-full text-[var(--muted-foreground)]">
      Loading...
    </div>
  );
}
