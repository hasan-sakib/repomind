"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatDateLabel } from "@/lib/analytics-time";
import { sumDailyCommits } from "@/lib/analytics-merge";
import type { ContributorActivity, DailyCommit } from "@/lib/types";
import { ChartEmpty } from "./chart-empty";
import { ChartTooltip } from "./chart-tooltip";

export function CommitFrequencyChart({
  dailyCommits,
  contributors,
  selectedContributor,
  onSelectContributor,
}: {
  dailyCommits: DailyCommit[];
  contributors: ContributorActivity[];
  selectedContributor: string | null;
  onSelectContributor: (login: string | null) => void;
}) {
  const data = sumDailyCommits(dailyCommits, selectedContributor);
  const hasActivity = data.some((d) => d.count > 0);
  const namedContributors = contributors.filter(
    (c): c is ContributorActivity & { login: string } => c.login !== null,
  );
  const selectedLabel = selectedContributor
    ? namedContributors.find((c) => c.login === selectedContributor)?.name ?? selectedContributor
    : "All contributors";

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-end">
        <Select
          value={selectedContributor ?? "all"}
          onValueChange={(value) => onSelectContributor(value === "all" ? null : value)}
        >
          <SelectTrigger className="h-7 w-44 text-xs">
            <SelectValue>{() => selectedLabel}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All contributors</SelectItem>
            {namedContributors.map((c) => (
              <SelectItem key={c.login} value={c.login}>
                {c.name ?? c.login}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {data.length < 2 || !hasActivity ? (
        <ChartEmpty message="Not enough commit history for this selection to plot a trend." />
      ) : (
        <ResponsiveContainer width="100%" height={200}>
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
            <Bar dataKey="count" name="Commits" fill="var(--color-chart-1)" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
