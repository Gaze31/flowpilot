"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";

import { missingFields } from "@/lib/steps";

// How each step type looks on the canvas
export const STEP_STYLES: Record<string, { icon: string; label: string; color: string }> = {
  "trigger.manual": { icon: "▶", label: "Manual trigger", color: "#f97316" },
  "trigger.schedule": { icon: "⏰", label: "Schedule", color: "#f97316" },
  "llm.prompt": { icon: "✨", label: "AI (Gemini)", color: "#a855f7" },
  "action.http": { icon: "🌐", label: "HTTP request", color: "#3b82f6" },
  "action.email": { icon: "✉", label: "Send email", color: "#22c55e" },
};

export type StepData = {
  stepType: string;
  stepId: string;
  config: Record<string, unknown>;
  runStatus?: "waiting" | "succeeded" | "failed";
  durationMs?: number | null;
};

export function StepNode({ data }: NodeProps) {
  const { stepType, stepId, config, runStatus, durationMs } = data as StepData;
  const style = STEP_STYLES[stepType] ?? { icon: "■", label: stepType, color: "#64748b" };
  const isTrigger = stepType.startsWith("trigger.");
  const missing = missingFields(stepType, config);
  const handleStyle = { width: 14, height: 14, backgroundColor: style.color, border: "2px solid #18181b" };

  let note = stepId;
  let noteColor = "text-zinc-400";
  if (missing.length > 0) {
    note = `${stepId} · ⚠ needs ${missing.join(", ")}`;
    noteColor = "text-amber-400";
  } else if (runStatus === "succeeded") {
    note = `${stepId} · ✓ ${durationMs ?? 0} ms`;
    noteColor = "text-green-400";
  } else if (runStatus === "failed") {
    note = `${stepId} · ✗ failed`;
    noteColor = "text-red-400";
  } else if (runStatus === "waiting") {
    note = `${stepId} · ⏳ waiting`;
    noteColor = "text-zinc-300";
  }

  const glow =
    runStatus === "succeeded" ? "0 0 0 4px #22c55e55" : runStatus === "failed" ? "0 0 0 4px #ef444488" : undefined;

  return (
    <div
      className="flex w-56 items-center gap-3 rounded-xl border-2 bg-zinc-900 px-4 py-3 shadow-lg"
      style={{ borderColor: style.color, boxShadow: glow }}
    >
      {!isTrigger && <Handle type="target" position={Position.Left} style={handleStyle} />}
      <div
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-xl"
        style={{ backgroundColor: style.color + "33", color: style.color }}
      >
        {style.icon}
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-zinc-100">{style.label}</p>
        <p className={`truncate text-xs ${noteColor}`}>{note}</p>
      </div>
      <Handle type="source" position={Position.Right} style={handleStyle} />
    </div>
  );
}