"use client";

import { useCallback, useState, type DragEvent } from "react";
import {
  addEdge,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { saveWorkflowGraph, type Workflow } from "@/lib/api";
import { missingFields } from "@/lib/steps";
import { SettingsPanel } from "./SettingsPanel"; // ← NEW
import { Sidebar } from "./Sidebar";
import { StepNode, type StepData } from "./StepNode";

const nodeTypes = { step: StepNode };
const EDGE_STYLE = { stroke: "#a1a1aa", strokeWidth: 2 };

function toCanvas(workflow: Workflow): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = workflow.graph.nodes.map((n, i) => ({
    id: n.id,
    type: "step",
    position: n.position ?? { x: i * 300, y: 0 },
    data: { stepType: n.type, stepId: n.id, config: n.config },
  }));
  const edges: Edge[] = workflow.graph.edges.map((e) => ({
    id: `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    animated: true,
    style: EDGE_STYLE,
  }));
  return { nodes, edges };
}

function toGraph(nodes: Node[], edges: Edge[]): Workflow["graph"] {
  return {
    nodes: nodes.map((n) => {
      const data = n.data as StepData;
      return {
        id: n.id,
        type: data.stepType,
        config: data.config,
        position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
      };
    }),
    edges: edges.map((e) => ({ source: e.source, target: e.target })),
  };
}

function nextStepId(nodes: Node[]): string {
  const numbers = nodes
    .map((n) => Number(n.id.replace(/^n/, "")))
    .filter((num) => !Number.isNaN(num));
  return `n${Math.max(0, ...numbers) + 1}`;
}

function Editor({ workflow }: { workflow: Workflow }) {
  const initial = toCanvas(workflow);
  const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);
  const { screenToFlowPosition } = useReactFlow();
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [saveError, setSaveError] = useState("");

  // ← NEW: which step is clicked (only when exactly one is selected)
  const selectedNodes = nodes.filter((n) => n.selected);
  const selected = selectedNodes.length === 1 ? selectedNodes[0] : undefined;

  // ← NEW: replace one step's settings
  function updateConfig(nodeId: string, config: Record<string, unknown>) {
    setNodes((current) =>
      current.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, config } } : n)),
    );
    setSaveState("idle");
  }

  async function handleSave() {
    const problems = nodes.flatMap((n) => {
      const data = n.data as StepData;
      const missing = missingFields(data.stepType, data.config);
      return missing.length > 0 ? [`${n.id} needs ${missing.join(", ")}`] : [];
    });
    if (problems.length > 0) {
      setSaveError(problems.join("; "));
      setSaveState("error");
      return;
    }

    setSaveState("saving");
    try {
      await saveWorkflowGraph(workflow.id, toGraph(nodes, edges));
      setSaveState("saved");
    } catch (e) {
      setSaveError((e as Error).message);
      setSaveState("error");
    }
  }

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((current) => addEdge({ ...connection, animated: true, style: EDGE_STYLE }, current));
    },
    [setEdges],
  );

  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();
      const stepType = event.dataTransfer.getData("application/flowpilot");
      if (!stepType) return;

      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
      setNodes((current) => {
        const id = nextStepId(current);
        return [...current, { id, type: "step", position, data: { stepType, stepId: id, config: {} } }];
      });
    },
    [screenToFlowPosition, setNodes],
  );

  return (
    <div className="flex h-full">
      <Sidebar />
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDragOver={onDragOver}
          onDrop={onDrop}
          nodeTypes={nodeTypes}
          forceColorMode="dark"
          fitView
          fitViewOptions={{ maxZoom: 1 }}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          <Controls />
          <MiniMap pannable zoomable />
          <Panel position="top-right" className="flex items-center gap-3">
            {saveState === "saved" && <span className="text-sm text-green-400">Saved ✓</span>}
            {saveState === "error" && <span className="max-w-md text-sm text-red-400">Save failed: {saveError}</span>}
            <button
              onClick={handleSave}
              disabled={saveState === "saving"}
              className="rounded-md bg-orange-500 px-4 py-1.5 text-sm font-semibold text-white hover:bg-orange-600 disabled:opacity-50"
            >
              {saveState === "saving" ? "Saving..." : "Save"}
            </button>
          </Panel>
        </ReactFlow>
      </div>
      {/* ← NEW: the settings panel, only when a step is clicked */}
      {selected && (
        <SettingsPanel
          key={selected.id}
          stepId={selected.id}
          stepType={(selected.data as StepData).stepType}
          config={(selected.data as StepData).config}
          onChange={(config) => updateConfig(selected.id, config)}
        />
      )}
    </div>
  );
}

export function FlowCanvas({ workflow }: { workflow: Workflow }) {
  return (
    <ReactFlowProvider>
      <Editor workflow={workflow} />
    </ReactFlowProvider>
  );
}