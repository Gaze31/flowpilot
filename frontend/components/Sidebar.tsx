"use client";

import type { DragEvent } from "react";
import { STEP_STYLES } from "./StepNode";

export function Sidebar() {
  function onDragStart(event: DragEvent<HTMLDivElement>, stepType: string) {
    event.dataTransfer.setData("application/flowpilot", stepType);
    event.dataTransfer.effectAllowed = "move";
  }

  return (
    <aside className="w-60 shrink-0 border-r border-zinc-800 bg-zinc-950 p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">Steps</p>
      <div className="flex flex-col gap-2">
        {Object.entries(STEP_STYLES).map(([stepType, style]) => (
          <div
            key={stepType}
            draggable
            onDragStart={(event) => onDragStart(event, stepType)}
            className="flex cursor-grab items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 hover:border-zinc-600"
          >
            <span
              className="flex h-8 w-8 items-center justify-center rounded-md"
              style={{ backgroundColor: style.color + "33", color: style.color }}
            >
              {style.icon}
            </span>
            <span className="text-sm text-zinc-200">{style.label}</span>
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs text-zinc-500">Drag a step onto the canvas.</p>
    </aside>
  );
}