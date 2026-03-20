"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { usePipelines } from "@/hooks/use-pipelines";
import { RunStateBadge } from "@/components/runs/run-state-badge";
import { formatTime, cn } from "@/lib/utils";
import { createPipeline, getPipelineTemplates } from "@/lib/api-client";
import { useSessions } from "@/hooks/use-sessions";
import type { PipelineTemplate, PipelineCreate } from "@/types/pipeline";

export default function PipelinesPage() {
  const { pipelines, isLoading, refresh } = usePipelines();
  const { sessions } = useSessions();
  const [templates, setTemplates] = useState<PipelineTemplate[] | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);

  const loadTemplates = useCallback(async () => {
    if (templates) return;
    try {
      const res = await getPipelineTemplates();
      setTemplates(res);
    } catch {
      // ignore
    }
  }, [templates]);

  async function handleCreateFromTemplate(template: PipelineTemplate) {
    if (!sessions.length) {
      alert("Create a chat session first.");
      return;
    }
    setCreating(true);
    try {
      const data: PipelineCreate = {
        name: template.name,
        description: template.description,
        session_id: sessions[0].id,
        steps: template.steps,
      };
      await createPipeline(data);
      await refresh();
      setShowCreate(false);
    } catch (err) {
      alert(`Failed to create pipeline: ${err}`);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">Pipelines</h2>
        <button
          onClick={() => {
            setShowCreate(!showCreate);
            loadTemplates();
          }}
          className="px-3 py-1.5 rounded-lg text-sm bg-[var(--accent)] text-[var(--accent-foreground)] hover:opacity-80"
        >
          {showCreate ? "Cancel" : "New Pipeline"}
        </button>
      </div>

      {showCreate && templates && (
        <div className="mb-6 space-y-3">
          <h3 className="text-sm font-semibold text-[var(--muted-foreground)]">
            Choose a template
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {templates.map((t) => (
              <button
                key={t.name}
                onClick={() => handleCreateFromTemplate(t)}
                disabled={creating}
                className={cn(
                  "p-4 border border-[var(--border)] rounded-lg text-left hover:bg-[var(--muted)] transition-colors",
                  creating && "opacity-50 cursor-not-allowed",
                )}
              >
                <div className="font-medium text-sm mb-1">{t.name}</div>
                <div className="text-xs text-[var(--muted-foreground)] mb-2">
                  {t.description}
                </div>
                <div className="text-xs text-[var(--muted-foreground)]">
                  {t.steps.length} steps
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-[var(--muted-foreground)]">Loading...</div>
      ) : pipelines.length === 0 ? (
        <div className="text-center py-12 text-[var(--muted-foreground)]">
          No pipelines yet. Create one from a template above.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted-foreground)]">
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">State</th>
                <th className="px-4 py-2 font-medium">Progress</th>
                <th className="px-4 py-2 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {pipelines.map((p) => (
                <tr
                  key={p.id}
                  className="border-b border-[var(--border)] hover:bg-[var(--muted)] transition-colors"
                >
                  <td className="px-4 py-2">
                    <Link
                      href={`/pipelines/${p.id}`}
                      className="text-[var(--accent)] hover:underline font-medium"
                    >
                      {p.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2">
                    <RunStateBadge state={p.state} />
                  </td>
                  <td className="px-4 py-2 text-[var(--muted-foreground)]">
                    {p.current_step}/{p.total_steps}
                  </td>
                  <td className="px-4 py-2 text-[var(--muted-foreground)]">
                    {formatTime(p.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
