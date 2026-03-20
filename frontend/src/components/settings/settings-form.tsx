"use client";

import { useHealth } from "@/hooks/use-health";
import { getServiceInfo, getSystemInfo } from "@/lib/api-client";
import { useEffect, useState } from "react";
import type { ServiceInfo } from "@/types/wes";
import type { SystemInfo } from "@/types/system-info";

function formatCtx(n: number): string {
  if (n >= 1024) return `${Math.round(n / 1024)}K`;
  return String(n);
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value == null) return null;
  return (
    <>
      <dt className="text-[var(--muted-foreground)]">{label}</dt>
      <dd>{value}</dd>
    </>
  );
}

export function SettingsForm() {
  const { health } = useHealth();
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);
  const [serviceInfo, setServiceInfo] = useState<ServiceInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const errors: string[] = [];
    Promise.allSettled([
      getSystemInfo().then(setSysInfo).catch((e) => errors.push(`System info: ${e.message}`)),
      getServiceInfo().then(setServiceInfo).catch((e) => errors.push(`Service info: ${e.message}`)),
    ]).finally(() => {
      if (errors.length) setError(errors.join("; "));
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="space-y-8 max-w-2xl">
        {[1, 2, 3].map((i) => (
          <div key={i} className="space-y-3">
            <div className="h-4 w-32 rounded bg-[var(--border)] animate-pulse" />
            <div className="h-20 rounded bg-[var(--border)] animate-pulse" />
          </div>
        ))}
      </div>
    );
  }

  const m = sysInfo?.model;
  const o = sysInfo?.ollama;
  const g = sysInfo?.gpu;
  const w = sysInfo?.worker;

  return (
    <div className="space-y-8 max-w-2xl">
      {error && (
        <div className="text-sm text-[var(--destructive)] bg-red-50 dark:bg-red-900/20 rounded-lg px-4 py-2">
          Failed to load: {error}
        </div>
      )}
      {/* LLM Model */}
      {m && (
        <section>
          <h3 className="text-sm font-medium mb-3">LLM Model</h3>
          <dl className="grid grid-cols-[140px_1fr] gap-x-6 gap-y-2 text-sm">
            <Row label="Model" value={m.name} />
            <Row label="Source" value={sysInfo?.source} />
            <Row label="Family" value={m.family} />
            <Row label="Parameters" value={m.parameter_size} />
            <Row label="Quantization" value={m.quantization} />
            <Row
              label="Context Length"
              value={m.context_length ? formatCtx(m.context_length) + " tokens" : null}
            />
            <Row label="MoE Experts" value={m.experts} />
          </dl>
        </section>
      )}

      {/* Ollama / Inference Server */}
      {o && (
        <section>
          <h3 className="text-sm font-medium mb-3">Inference Server</h3>
          <dl className="grid grid-cols-[140px_1fr] gap-x-6 gap-y-2 text-sm">
            <Row label="Ollama" value={o.version ? `v${o.version}` : null} />
            <Row
              label="Status"
              value={
                <span className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${o.model_loaded ? "bg-green-500" : "bg-yellow-500"}`}
                  />
                  {o.model_loaded ? "Model loaded" : "No model loaded"}
                </span>
              }
            />
            <Row
              label="Model Size"
              value={o.model_size_gb ? `${o.model_size_gb} GB` : null}
            />
            <Row
              label="VRAM Used"
              value={o.vram_used_gb ? `${o.vram_used_gb} GB` : null}
            />
            {o.gpu_count && <Row label="GPUs" value={o.gpu_count} />}
          </dl>
        </section>
      )}

      {/* GPU */}
      {g && g.devices.length > 0 && (
        <section>
          <h3 className="text-sm font-medium mb-3">GPU</h3>
          <dl className="grid grid-cols-[140px_1fr] gap-x-6 gap-y-2 text-sm">
            {g.devices.map((dev, i) => (
              <Row
                key={i}
                label={g.devices.length > 1 ? `GPU ${i}` : "Device"}
                value={`${dev.name} (${Math.round(dev.memory_total_mb / 1024)} GB)`}
              />
            ))}
            {g.devices[0]?.memory_used_mb != null && (
              <Row
                label="VRAM Usage"
                value={`${Math.round(g.devices[0].memory_used_mb / 1024)} / ${Math.round(g.devices[0].memory_total_mb / 1024)} GB`}
              />
            )}
            <Row label="Driver" value={g.driver_version} />
          </dl>
        </section>
      )}

      {/* System Status */}
      <section>
        <h3 className="text-sm font-medium mb-3">System Status</h3>
        <dl className="grid grid-cols-[140px_1fr] gap-x-6 gap-y-2 text-sm">
          <Row
            label="Backend"
            value={
              <span className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${health ? "bg-green-500" : "bg-red-500"}`}
                />
                {health ? "Connected" : "Offline"}
              </span>
            }
          />
          {health && (
            <>
              <Row
                label="Code Execution"
                value={health.celery_active ? "Celery active" : "In-process"}
              />
              <Row label="Version" value={health.version || "—"} />
            </>
          )}
          {w && (
            <Row
              label="Task Timeout"
              value={`${w.task_timeout}s`}
            />
          )}
          {sysInfo && (
            <Row
              label="Agent Timeout"
              value={`${sysInfo.timeout_seconds}s`}
            />
          )}
        </dl>
      </section>

      {/* WES Service Info */}
      {serviceInfo && (
        <section>
          <h3 className="text-sm font-medium mb-3">WES Service</h3>
          <dl className="grid grid-cols-[140px_1fr] gap-x-6 gap-y-2 text-sm">
            <Row
              label="WES Versions"
              value={serviceInfo.supported_wes_versions.join(", ")}
            />
            <Row
              label="Workflow Types"
              value={Object.keys(serviceInfo.workflow_type_versions).join(", ") || "—"}
            />
            <Row
              label="Engine"
              value={
                Object.entries(serviceInfo.workflow_engine_versions)
                  .map(([k, v]) => `${k} ${v}`)
                  .join(", ") || "—"
              }
            />
          </dl>
        </section>
      )}
    </div>
  );
}
