"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { ContributorActivity } from "@/lib/types";
import { cn } from "cn";
import { ChartEmpty } from "./chart-empty";
import { ChartTooltip } from "./chart-tooltip";

const MAX_SHOWN = 10;

export function ContributorLeaderboard({
  contributors,
  selectedContributor,
  onSelectContributor,
}: {
  contributors: ContributorActivity[];
  selectedContributor: string | null;
  onSelectContributor: (login: string | null) => void;
}) {
  if (contributors.length === 0) {
    return <ChartEmpty message="No contributor activity found in the sampled history yet." />;
  }

  const data = contributors.slice(0, MAX_SHOWN).map((c) => ({
    label: c.name ?? c.login ?? "Unknown",
    login: c.login,
    commits: c.commit_count,
    prs: c.pr_count,
  }));

  return (
    <div className="space-y-2">
      <ResponsiveContainer width="100%" height={Math.max(160, data.length * 32)}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 16, left: 8, bottom: 0 }}
          barCategoryGap={8}
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
            dataKey="label"
            width={110}
            tick={{ fontSize: 11, fill: "var(--color-foreground)" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<ChartTooltip />} />
          <Bar
            dataKey="commits"
            name="Commits"
            fill="var(--color-chart-1)"
            radius={[0, 2, 2, 0]}
            onClick={(entry) => {
              const login: string | null = entry.payload?.login ?? null;
              onSelectContributor(selectedContributor === login ? null : login);
            }}
            className="cursor-pointer"
          />
          <Bar dataKey="prs" name="Pull requests" fill="var(--color-chart-2)" radius={[0, 2, 2, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <p className={cn("text-xs text-muted-foreground", !selectedContributor && "invisible")}>
        Filtering commit frequency to a selected contributor — click their bar again to clear.
      </p>
    </div>
  );
}
