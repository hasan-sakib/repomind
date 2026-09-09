"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatDateLabel } from "@/lib/analytics-time";
import type { DailyPRIssueActivity } from "@/lib/types";
import { ChartEmpty } from "./chart-empty";
import { ChartTooltip } from "./chart-tooltip";

export function PrThroughputChart({ data }: { data: DailyPRIssueActivity[] }) {
  const hasActivity = data.some((d) => d.prs_opened + d.prs_merged + d.prs_closed > 0);
  if (data.length < 2 || !hasActivity) {
    return (
      <ChartEmpty message="No pull request activity in this time range. Try a wider range." />
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
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
          width={28}
        />
        <Tooltip content={<ChartTooltip />} />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 12, color: "var(--color-muted-foreground)" }}
        />
        <Bar dataKey="prs_opened" name="Opened" fill="var(--color-chart-1)" radius={[2, 2, 0, 0]} />
        <Bar dataKey="prs_merged" name="Merged" fill="var(--color-chart-3)" radius={[2, 2, 0, 0]} />
        <Bar dataKey="prs_closed" name="Closed (unmerged)" fill="var(--color-chart-5)" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
