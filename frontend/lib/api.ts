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