import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-56" />
        </div>
        <Skeleton className="h-8 w-40" />
      </div>
      <div className="space-y-2 rounded-lg border border-border p-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    </div>
  );
}
