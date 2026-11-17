"use client";

import { Background, BackgroundVariant, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { Workflow } from "@/lib/api";
import { StepNode } from "./StepNode";

const nodeTypes = { step: StepNode };

function toCanvas(workflow: Workflow): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = workflow.graph.nodes.map((n, i) => ({
    id: n.id,
    type: "step",
    position: n.position ?? { x: i * 300, y: 0 },
    data: { stepType: n.type, stepId: n.id },
  }));
  const edges: Edge[] = workflow.graph.edges.map((e) => ({
    id: `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    animated: true,
    style: { stroke: "#a1a1aa", strokeWidth: 2 },
  }));
  return { nodes, edges };
}

export function FlowCanvas({ workflow }: { workflow: Workflow }) {
  const { nodes, edges } = toCanvas(workflow);
  return (
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} forceColorMode="dark" fitView fitViewOptions={{ maxZoom: 1 }}>
      <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
      <Controls />
      <MiniMap pannable zoomable />
    </ReactFlow>
  );
}