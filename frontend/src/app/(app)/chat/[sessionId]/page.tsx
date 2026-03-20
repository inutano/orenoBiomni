"use client";

import { use } from "react";
import { ChatPanel } from "@/components/chat/chat-panel";

export default function ChatPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = use(params);

  return <ChatPanel sessionId={sessionId} />;
}
