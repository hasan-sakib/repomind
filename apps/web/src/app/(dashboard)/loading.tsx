import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="flex h-dvh w-full">
      <div className="hidden w-56 shrink-0 border-r border-border p-3 lg:block">
        <Skeleton className="mb-4 h-8 w-full" />
        <Skeleton className="mb-2 h-7 w-full" />
        <Skeleton className="h-7 w-full" />
      </div>
      <div className="flex-1 p-6">
        <Skeleton className="mb-4 h-6 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    </div>
  );
}
