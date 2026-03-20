"use client";

import { use } from "react";
import { RunDetail } from "@/components/runs/run-detail";

export default function RunDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = use(params);

  return <RunDetail runId={runId} />;
}
