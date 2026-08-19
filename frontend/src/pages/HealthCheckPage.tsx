import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";

interface HealthResponse {
  status: string;
  service: string;
}

async function fetchHealth(): Promise<HealthResponse> {
  // Deliberately calling /health directly (not via apiClient, which is
  // scoped to /api/v1) since health is intentionally outside the
  // versioned API -- it's an infra probe, not an API contract.
  const res = await fetch("/health");
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

export function HealthCheckPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background text-foreground">
      <h1 className="text-3xl font-bold">Kairos</h1>
      <p className="text-muted-foreground">Enterprise Decision Intelligence Platform</p>

      <div className="mt-4 rounded-lg border border-border p-6 text-center">
        {isLoading && <p>Checking backend connection…</p>}
        {isError && <p className="text-destructive">Backend unreachable</p>}
        {data && (
          <p>
            Backend status: <span className="font-mono text-primary">{data.status}</span> (
            {data.service})
          </p>
        )}
      </div>

      <Button onClick={() => refetch()}>Re-check connection</Button>
    </main>
  );
}
