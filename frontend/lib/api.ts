//Talks to the Flowpilot API. The address comes from .env.local.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type FlowNode = {
    id: string;
    type: string;
    config: Record<string, unknown>;
    position:{x:number; y: number} | null;
};

export type FlowEdge = {source:string; target:string};

export type Workflow = {
    id:string;
    name:string;
    garph:{nodes:FlowNode[]; edges:FlowEdge[]};
    created_at:string;
};

export async function listWorkflows(): Promise<Workflow[]>{
    const res = await fetch(`${API_URL}/workflows`);
    if(!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
}
// Saves through our own Next.js route (/api/...), which adds the API key on the server.
export async function saveWorkflowGraph(id: string, graph: Workflow["graph"]): Promise<Workflow> {
  const res = await fetch(`/api/workflows/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ graph }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ? JSON.stringify(body.detail) : `API error ${res.status}`);
  }
  return res.json();
}
export type RunStep = {
  node_id: string;
  attempt: number;
  status: "succeeded" | "failed";
  output: unknown;
  error: string | null;
  duration_ms: number | null;
};

export type Run = {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  error: string | null;
  steps: RunStep[];
};

// Starts a run through our own route (needs the key). Returns the new run's id.
export async function startRun(workflowId: string): Promise<string> {
  const res = await fetch(`/api/workflows/${workflowId}/runs`, { method: "POST" });
  if (!res.ok) throw new Error(`Could not start run (${res.status})`);
  const body = await res.json();
  return body.id;
}

// Reading a run is public, so this goes straight to the API.
export async function getRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_URL}/runs/${runId}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}