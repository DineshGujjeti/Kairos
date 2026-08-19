import { useQuery } from "@tanstack/react-query";
import { History, Database, Lightbulb } from "lucide-react";
import { Link } from "react-router-dom";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { decisionApi } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

export default function HistoryPage() {
  const { data: history, isLoading, isError } = useQuery({
    queryKey: ["decision-history"],
    queryFn: () => decisionApi.history().then(r => r.data),
  });

  return (
    <PageWrapper title="Decision History" subtitle="Past decision sessions and recommendations">
      <Card>
        <CardHeader><CardTitle>Recent Sessions</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">{[...Array(4)].map((_, i) => <div key={i} className="h-12 bg-muted rounded-xl animate-pulse" />)}</div>
          ) : isError ? (
            <EmptyState
              icon={History}
              tone="warning"
              title="Couldn't load history"
              description="Something went wrong fetching past sessions. Try refreshing the page."
            />
          ) : !history?.length ? (
            <EmptyState
              icon={History}
              title="No history yet"
              description="Decision sessions are saved automatically every time recommendations are generated for a dataset."
              action={<Link to="/decision"><Button size="sm" variant="outline" className="gap-1.5"><Lightbulb className="h-3.5 w-3.5" />Go to Decision Advisor</Button></Link>}
            />
          ) : (
            <div className="space-y-2">
              {history.map((s: any) => (
                <div key={s.id} className="flex items-center gap-3 p-3.5 rounded-xl border border-border hover:bg-accent transition-colors">
                  <div className="h-9 w-9 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                    <Database className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-foreground truncate">{s.summary || "Decision Session"}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{fmtDate(s.created_at)}</p>
                  </div>
                  <Badge variant="outline" className="capitalize">{s.session_type}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </PageWrapper>
  );
}
