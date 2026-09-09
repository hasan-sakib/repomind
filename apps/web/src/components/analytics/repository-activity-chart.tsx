"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartEmpty } from "./chart-empty";
import { ChartTooltip } from "./chart-tooltip";
import { formatDateLabel } from "@/lib/analytics-time";
import type { MergedDailyActivity } from "@/lib/analytics-merge";

export function RepositoryActivityChart({ data }: { data: MergedDailyActivity[] }) {
  const hasActivity = data.some((d) => d.commits + d.prs_opened + d.issues_opened > 0);
  if (data.length < 2 || !hasActivity) {
    return (
      <ChartEmpty message="Not enough activity in this time range to plot a trend. Try a wider range." />
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDateLabel}
          tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          axisLine={{ stroke: "var(--color-border)" }}
          tickLine={false}
          minTickGap={24}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
        />
        <Tooltip content={<ChartTooltip />} />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 12, color: "var(--color-muted-foreground)" }}
        />
        <Area
          type="monotone"
          dataKey="commits"
          name="Commits"
          stackId="activity"
          stroke="var(--color-chart-1)"
          fill="var(--color-chart-1)"
          fillOpacity={0.35}
        />
        <Area
          type="monotone"
          dataKey="prs_opened"
          name="PRs opened"
          stackId="activity"
          stroke="var(--color-chart-2)"
          fill="var(--color-chart-2)"
          fillOpacity={0.35}
        />
        <Area
          type="monotone"
          dataKey="issues_opened"
          name="Issues opened"
          stackId="activity"
          stroke="var(--color-chart-3)"
          fill="var(--color-chart-3)"
          fillOpacity={0.35}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
