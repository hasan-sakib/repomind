"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { KIND_ICON } from "@/components/architecture/node-kind-icon";
import { Badge } from "@/components/ui/badge";
import type { ArchitectureHotspot, FileHotspot, NodeKind } from "@/lib/types";
import { ChartEmpty } from "./chart-empty";

function HotspotTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: FileHotspot | ArchitectureHotspot }[];
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  const path = "path" in item ? item.path : item.package_path;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="max-w-56 truncate font-medium text-foreground">{path}</p>
      <p className="text-muted-foreground">
        Changed <span className="font-medium text-foreground">{item.change_count}</span> times
        {"dependents_count" in item && (
          <>
            {" "}
            · <span className="font-medium text-foreground">{item.dependents_count}</span>{" "}
            dependents
          </>
        )}
        {"file_count" in item && (
          <>
            {" "}
            · <span className="font-medium text-foreground">{item.file_count}</span> files
          </>
        )}
      </p>
    </div>
  );
}

function truncatePath(path: string, maxLength = 30): string {
  if (path.length <= maxLength) return path;
  return `…${path.slice(-(maxLength - 1))}`;
}

export function FileHotspotsChart({ hotspots }: { hotspots: FileHotspot[] }) {
  if (hotspots.length === 0) {
    return (
      <ChartEmpty message="No file-change history found in the sampled commits yet." />
    );
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, hotspots.length * 28)}>
      <BarChart
        data={hotspots}
        layout="vertical"
        margin={{ top: 4, right: 24, left: 8, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
        />
        <YAxis
          type="category"
          dataKey="path"
          width={180}
          tickFormatter={(path: string) => truncatePath(path)}
          tick={{ fontSize: 11, fill: "var(--color-foreground)", fontFamily: "var(--font-mono)" }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<HotspotTooltip />} />
        <Bar dataKey="change_count" name="Changes" fill="var(--color-chart-2)" radius={[0, 2, 2, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ArchitectureHotspotsChart({ hotspots }: { hotspots: ArchitectureHotspot[] }) {
  if (hotspots.length === 0) {
    return <ChartEmpty message="No package-level change history found yet." />;
  }

  return (
    <div className="space-y-2">
      <ResponsiveContainer width="100%" height={Math.max(160, hotspots.length * 32)}>
        <BarChart
          data={hotspots}
          layout="vertical"
          margin={{ top: 4, right: 24, left: 8, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
          />
          <YAxis
            type="category"
            dataKey="package_path"
            width={180}
            tickFormatter={(path: string) => truncatePath(path || "(root)")}
            tick={{ fontSize: 11, fill: "var(--color-foreground)", fontFamily: "var(--font-mono)" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<HotspotTooltip />} />
          <Bar dataKey="change_count" name="Changes" fill="var(--color-chart-4)" radius={[0, 2, 2, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap gap-1.5">
        {hotspots.slice(0, 6).map((h) => {
          const Icon = KIND_ICON[h.kind as NodeKind];
          return (
            <Badge key={h.package_path} variant="outline" className="text-[10px]">
              <Icon className="size-3" />
              {h.package_path || "(root)"}
            </Badge>
          );
        })}
      </div>
    </div>
  );
}
