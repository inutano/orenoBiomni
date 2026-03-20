"use client";

import { cn } from "@/lib/utils";
import { RunStateBadge } from "@/components/runs/run-state-badge";
import type { StepResult } from "@/types/pipeline";
import type { State } from "@/types/wes";

const jobTypeBadgeColors: Record<string, string> = {
  python: "bg-blue-50 text-blue-700 border-blue-200",
  r: "bg-purple-50 text-purple-700 border-purple-200",
  bash: "bg-gray-50 text-gray-700 border-gray-200",
};

function StepIcon({ state }: { state: State }) {
  const base = "w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0";

  switch (state) {
    case "COMPLETE":
      return <span className={cn(base, "bg-green-500 text-white")}>&#10003;</span>;
    case "RUNNING":
      return <span className={cn(base, "bg-blue-500 text-white animate-pulse")}>&#9654;</span>;
    case "EXECUTOR_ERROR":
    case "SYSTEM_ERROR":
      return <span className={cn(base, "bg-red-500 text-white")}>&#10005;</span>;
    case "CANCELED":
      return <span className={cn(base, "bg-gray-400 text-white")}>&mdash;</span>;
    default:
      return <span className={cn(base, "bg-gray-200 text-gray-500")}>&middot;</span>;
  }
}

function StepConnector({ state }: { state: State }) {
  const completed = state === "COMPLETE";
  return (
    <div
      className={cn(
        "flex-1 h-0.5 mx-1",
        completed ? "bg-green-400" : "bg-gray-200",
      )}
    />
  );
}

export function PipelineProgress({ steps }: { steps: StepResult[] }) {
  return (
    <div className="space-y-3">
      {/* Horizontal progress bar */}
      <div className="flex items-center gap-0">
        {steps.map((step, i) => (
          <div key={step.index} className="flex items-center flex-1 min-w-0">
            <StepIcon state={step.state} />
            {i < steps.length - 1 && <StepConnector state={step.state} />}
          </div>
        ))}
      </div>

      {/* Step details */}
      <div className="flex gap-1">
        {steps.map((step) => (
          <div
            key={step.index}
            className={cn(
              "flex-1 min-w-0 p-2 rounded border text-xs",
              step.state === "RUNNING"
                ? "border-blue-300 bg-blue-50"
                : "border-[var(--border)] bg-[var(--background)]",
            )}
          >
            <div className="font-medium truncate mb-1">{step.name}</div>
            <div className="flex items-center gap-1 flex-wrap">
              <span
                className={cn(
                  "inline-flex px-1.5 py-0.5 rounded text-[10px] border",
                  jobTypeBadgeColors[step.job_type] || jobTypeBadgeColors.bash,
                )}
              >
                {step.job_type}
              </span>
              <RunStateBadge state={step.state} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
