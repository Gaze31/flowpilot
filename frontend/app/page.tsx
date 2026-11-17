"use client";

import { useEffect, useState } from "react";

import { FlowCanvas } from "@/components/FlowCanvas";
import { listWorkflows, type Workflow } from "@/lib/api";

export default function Home() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    listWorkflows()
      .then((list) => {
        setWorkflows(list);
        if (list.length > 0) setSelectedId(list[0].id);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const selected = workflows.find((w) => w.id === selectedId);

  return (
    <main className="flex h-screen flex-col bg-zinc-950 text-zinc-100">
      <header className="flex items-center gap-4 border-b border-zinc-800 px-6 py-3">
        <h1 className="text-lg font-bold">
          Flow<span className="text-orange-500">Pilot</span>
        </h1>
        <select
          className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {workflows.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
      </header>

      <div className="flex-1">
        {error && <p className="p-6 text-red-400">Could not load workflows: {error}</p>}
        {!error && !selected && <p className="p-6 text-zinc-400">Loading...</p>}
        {selected && <FlowCanvas key={selected.id} workflow={selected} />}
      </div>
    </main>
  );
}
