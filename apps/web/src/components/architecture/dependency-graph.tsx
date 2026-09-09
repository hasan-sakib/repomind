"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  type Edge,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { GraphEdge, GraphNode } from "@/lib/types";
import { GraphNodeComponent, type ArchNode } from "./graph-node";
import { layoutWithDagre } from "./layout";

const nodeTypes = { architecture: GraphNodeComponent };

export function DependencyGraph({
  nodes,
  edges,
  selectedNodeId,
  onNodeClick,
  onNodeDoubleClick,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  onNodeClick: (node: GraphNode) => void;
  onNodeDoubleClick?: (node: GraphNode) => void;
}) {
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  const laidOutNodes = useMemo(() => {
    const flowNodes: ArchNode[] = nodes.map((node) => ({
      id: node.id,
      type: "architecture",
      position: { x: 0, y: 0 },
      data: { original: node },
      selected: node.id === selectedNodeId,
    }));
    const flowEdges: Edge[] = edges.map((edge) => ({
      id: `${edge.source}->${edge.target}`,
      source: edge.source,
      target: edge.target,
    }));
    return layoutWithDagre(flowNodes, flowEdges);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges]);

  const flowEdges: Edge[] = useMemo(
    () =>
      edges.map((edge) => ({
        id: `${edge.source}->${edge.target}`,
        source: edge.source,
        target: edge.target,
        style: { strokeWidth: Math.min(1 + edge.weight * 0.4, 3) },
        markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
      })),
    [edges],
  );

  const displayNodes = laidOutNodes.map((node) => ({
    ...node,
    selected: node.id === selectedNodeId,
  }));

  const handleNodeClick: NodeMouseHandler<ArchNode> = (_event, node) => {
    const original = byId.get(node.id);
    if (original) onNodeClick(original);
  };

  const handleNodeDoubleClick: NodeMouseHandler<ArchNode> = (_event, node) => {
    const original = byId.get(node.id);
    if (original && onNodeDoubleClick) onNodeDoubleClick(original);
  };

  return (
    <ReactFlow
      nodes={displayNodes}
      edges={flowEdges}
      nodeTypes={nodeTypes}
      onNodeClick={handleNodeClick}
      onNodeDoubleClick={handleNodeDoubleClick}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.1}
      maxZoom={2}
      nodesConnectable={false}
      edgesFocusable={false}
      elevateNodesOnSelect={false}
    >
      <Background gap={20} />
      <Controls showInteractive={false} />
      <MiniMap pannable zoomable className="bg-card!" />
    </ReactFlow>
  );
}
