import { Skeleton } from "@/components/ui/skeleton";

export function PageLoading() {
  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Skeleton className="h-64 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
      <Skeleton className="h-48 rounded-xl" />
    </div>
  );
}

export function CardLoading({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3 p-5">
      {[...Array(rows)].map((_, i) => <Skeleton key={i} className="h-4 rounded" style={{ width: `${70 + (i % 3) * 10}%` }} />)}
    </div>
  );
}
