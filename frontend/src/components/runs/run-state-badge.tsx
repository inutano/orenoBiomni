import { cn } from "@/lib/utils";
import type { State } from "@/types/wes";

const stateColors: Record<State, string> = {
  UNKNOWN: "bg-gray-200 text-gray-700",
  QUEUED: "bg-yellow-100 text-yellow-800",
  INITIALIZING: "bg-blue-100 text-blue-800",
  RUNNING: "bg-blue-200 text-blue-900",
  PAUSED: "bg-orange-100 text-orange-800",
  COMPLETE: "bg-green-100 text-green-800",
  EXECUTOR_ERROR: "bg-red-100 text-red-800",
  SYSTEM_ERROR: "bg-red-200 text-red-900",
  CANCELED: "bg-gray-100 text-gray-600",
  CANCELING: "bg-orange-200 text-orange-900",
  PREEMPTED: "bg-purple-100 text-purple-800",
};

export function RunStateBadge({ state }: { state: State }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        stateColors[state] || stateColors.UNKNOWN,
      )}
    >
      {state}
    </span>
  );
}
