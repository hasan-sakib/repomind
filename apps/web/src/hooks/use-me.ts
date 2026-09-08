import { useQuery, useQueryClient } from "@tanstack/react-query";

import { getMe } from "@/lib/api/auth";
import type { MeResponse } from "@/lib/types";

export const ME_QUERY_KEY = ["me"] as const;

export function useMeQuery(initialData?: MeResponse) {
  return useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: getMe,
    initialData,
    staleTime: 60_000,
    retry: false,
  });
}

export function useInvalidateMe() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY });
}
