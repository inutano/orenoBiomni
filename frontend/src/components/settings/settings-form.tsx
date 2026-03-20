"use client";

import { useHealth } from "@/hooks/use-health";
import { useSessions } from "@/hooks/use-sessions";
import { getServiceInfo, getSession } from "@/lib/api-client";
import { useEffect, useState } from "react";
import type { ServiceInfo } from "@/types/wes";

export function SettingsForm() {
  const { health } = useHealth();
  const { sessions } = useSessions();
  const [serviceInfo, setServiceInfo] = useState<ServiceInfo | null>(null);
  const [agentConfig, setAgentConfig] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    getServiceInfo()
      .then(setServiceInfo)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (sessions.length > 0) {
      getSession(sessions[0].id)
        .then((s) => setAgentConfig(s.agent_config))
        .catch(() => {});
    }
  }, [sessions]);

  const llmConfig = agentConfig?.llm_config as Record<string, unknown> | undefined;
  const modelName = (llmConfig?.model as string) || null;
  const modelSource = (llmConfig?.api_base as string) || (llmConfig?.base_url as string) || null;

  return (
    <div className="space-y-8 max-w-2xl">
      <section>
        <h3 className="text-sm font-medium mb-3">System Status</h3>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
          <dt className="text-[var(--muted-foreground)]">Backend</dt>
          <dd className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${health ? "bg-green-500" : "bg-red-500"}`} />
            {health ? "Connected" : "Offline"}
          </dd>
          {health && (
            <>
              <dt className="text-[var(--muted-foreground)]">Celery</dt>
              <dd>{health.celery_active ? "Active" : "Inactive"}</dd>
              <dt className="text-[var(--muted-foreground)]">Version</dt>
              <dd>{health.version || "—"}</dd>
            </>
          )}
        </dl>
      </section>

      {(modelName || modelSource) && (
        <section>
          <h3 className="text-sm font-medium mb-3">Agent Configuration</h3>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
            {modelName && (
              <>
                <dt className="text-[var(--muted-foreground)]">LLM Model</dt>
                <dd>{modelName}</dd>
              </>
            )}
            {modelSource && (
              <>
                <dt className="text-[var(--muted-foreground)]">Source</dt>
                <dd className="truncate">{modelSource}</dd>
              </>
            )}
          </dl>
        </section>
      )}

      {serviceInfo && (
        <section>
          <h3 className="text-sm font-medium mb-3">WES Service Info</h3>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
            <dt className="text-[var(--muted-foreground)]">WES Versions</dt>
            <dd>{serviceInfo.supported_wes_versions.join(", ")}</dd>
            <dt className="text-[var(--muted-foreground)]">Workflow Types</dt>
            <dd>
              {Object.keys(serviceInfo.workflow_type_versions).join(", ") || "—"}
            </dd>
            <dt className="text-[var(--muted-foreground)]">Engine</dt>
            <dd>
              {Object.entries(serviceInfo.workflow_engine_versions)
                .map(([k, v]) => `${k} ${v}`)
                .join(", ") || "—"}
            </dd>
          </dl>
        </section>
      )}
    </div>
  );
}
