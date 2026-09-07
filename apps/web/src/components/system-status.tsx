"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";

interface HealthResponse {
  status: string;
  environment: string;
}

export function SystemStatus() {
  const { data, isPending, isError } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<HealthResponse>("/api/v1/health"),
    retry: false,
  });

  if (isPending) {
    return <Badge variant="secondary">Checking API…</Badge>;
  }

  if (isError) {
    return <Badge variant="destructive">API unreachable</Badge>;
  }

  return (
    <Badge variant="outline">
      API {data.status} · {data.environment}
    </Badge>
  );
}
