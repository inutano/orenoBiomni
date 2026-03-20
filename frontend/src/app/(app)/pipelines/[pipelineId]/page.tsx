"use client";

import { useParams } from "next/navigation";
import { usePipeline } from "@/hooks/use-pipelines";
import { PipelineProgress } from "@/components/pipelines/pipeline-progress";
import { RunStateBadge } from "@/components/runs/run-state-badge";
import { formatTime } from "@/lib/utils";
import { TERMINAL_STATES } from "@/types/wes";
import Link from "next/link";

export default function PipelineDetailPage() {
  const params = useParams();
  const pipelineId = params.pipelineId as string;
  const { pipeline, isLoading, cancel } = usePipeline(pipelineId);

  if (isLoading || !pipeline) {
    return (
      <div className="p-6 text-[var(--muted-foreground)]">Loading...</div>
    );
  }

  const isActive = !TERMINAL_STATES.includes(pipeline.state);

  return (
    <div className="p-6 max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link
            href="/pipelines"
            className="text-sm text-[var(--muted-foreground)] hover:underline"
          >
            &larr; Pipelines
          </Link>
          <h2 className="text-lg font-bold mt-1">{pipeline.name}</h2>
          {pipeline.description && (
            <p className="text-sm text-[var(--muted-foreground)]">
              {pipeline.description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <RunStateBadge state={pipeline.state} />
          {isActive && (
            <button
              onClick={cancel}
              className="px-3 py-1.5 rounded-lg text-sm border border-red-300 text-red-600 hover:bg-red-50"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      <div className="text-sm text-[var(--muted-foreground)] flex gap-4">
        <span>
          Progress: {pipeline.current_step}/{pipeline.total_steps}
        </span>
        <span>Created: {formatTime(pipeline.created_at)}</span>
        {pipeline.started_at && (
          <span>Started: {formatTime(pipeline.started_at)}</span>
        )}
        {pipeline.completed_at && (
          <span>Completed: {formatTime(pipeline.completed_at)}</span>
        )}
      </div>

      <PipelineProgress steps={pipeline.steps} />

      {/* Step details with output */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold">Step Details</h3>
        {pipeline.steps.map((step) => (
          <div
            key={step.index}
            className="border border-[var(--border)] rounded-lg p-4 space-y-2"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{step.name}</span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">
                  {step.job_type}
                </span>
              </div>
              <RunStateBadge state={step.state} />
            </div>
            <pre className="text-xs bg-[var(--muted)] p-2 rounded overflow-x-auto">
              {step.code}
            </pre>
            {step.stdout && (
              <div>
                <div className="text-xs font-medium text-[var(--muted-foreground)] mb-1">
                  Output
                </div>
                <pre className="text-xs bg-green-50 text-green-900 p-2 rounded overflow-x-auto whitespace-pre-wrap">
                  {step.stdout}
                </pre>
              </div>
            )}
            {step.stderr && (
              <div>
                <div className="text-xs font-medium text-red-600 mb-1">
                  Error
                </div>
                <pre className="text-xs bg-red-50 text-red-900 p-2 rounded overflow-x-auto whitespace-pre-wrap">
                  {step.stderr}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
