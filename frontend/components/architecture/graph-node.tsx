import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";

import { cn } from "cn";
import type { GraphNode } from "@/lib/types";
import { KIND_ICON } from "./node-kind-icon";

export type ArchNode = Node<{ original: GraphNode }, "architecture">;

const KIND_LABEL: Record<GraphNode["kind"], string> = {
  route: "Route",
  service: "Service",
  repository: "Repository",
  model: "Model",
  schema: "Schema",
  other: "Module",
  database: "Database",
};

function GraphNodeCard({ data, selected }: NodeProps<ArchNode>) {
  const node = data.original;
  const Icon = KIND_ICON[node.kind];

  return (
    <div
      className={cn(
        "min-w-40 rounded-lg border bg-card px-3 py-2 text-xs shadow-sm transition-colors",
        selected ? "border-brand ring-2 ring-brand/20" : "border-border",
        node.node_type === "database" && "bg-muted",
      )}
    >
      <Handle type="target" position={Position.Top} className="!size-1.5 !border-none !bg-border" />
      <div className="flex items-center gap-1.5 text-muted-foreground">
        <Icon className="size-3.5 shrink-0" aria-hidden="true" />
        <span className="text-[10px] font-medium tracking-wide uppercase">
          {KIND_LABEL[node.kind]}
        </span>
      </div>
      <p className="mt-0.5 truncate font-medium text-foreground" title={node.label}>
        {node.label}
      </p>
      {node.node_type === "package" && (
        <p className="text-muted-foreground">
          {node.file_count} {node.file_count === 1 ? "file" : "files"}
        </p>
      )}
      {node.node_type === "file" && node.symbol_count !== null && (
        <p className="text-muted-foreground">
          {node.symbol_count} {node.symbol_count === 1 ? "symbol" : "symbols"}
        </p>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!size-1.5 !border-none !bg-border"
      />
    </div>
  );
}

export const GraphNodeComponent = memo(GraphNodeCard);
