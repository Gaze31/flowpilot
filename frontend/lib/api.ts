// Every call goes to our own Next.js routes (/api/...). They talk to the FlowPilot API on the server,
// so the browser only ever talks to this site, and the API key never reaches the browser.

// The public demo sets this to "true": it hides every editing control.
export const READ_ONLY = process.env.NEXT_PUBLIC_READ_ONLY === "true";

export type FlowNode = {
  id: string;
  type: string;
  config: Record<string, unknown>;
  position: { x: number; y: number } | null;
};

export type FlowEdge = { source: string; target: string };

export type Workflow = {
  id: string;
  name: string;
  graph: { nodes: FlowNode[]; edges: FlowEdge[] };
  created_at: string;
};

export type RunStep = {
  node_id: string;
  attempt: number;
  status: "succeeded" | "failed";
  input: unknown;
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

export type RunSummary = Omit<Run, "steps">;

// Reads: public, no key needed.
export async function listWorkflows(): Promise<Workflow[]> {
  const res = await fetch("/api/workflows");
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export async function getRun(runId: string): Promise<Run> {
  const res = await fetch(`/api/runs/${runId}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

// The API returns the newest run first, without steps.
export async function listRuns(workflowId: string): Promise<RunSummary[]> {
  const res = await fetch(`/api/workflows/${workflowId}/runs`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

// Writes: the route adds the API key on the server.
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

export async function startRun(workflowId: string): Promise<string> {
  const res = await fetch(`/api/workflows/${workflowId}/runs`, { method: "POST" });
  if (!res.ok) throw new Error(`Could not start run (${res.status})`);
  const body = await res.json();
  return body.id;
}