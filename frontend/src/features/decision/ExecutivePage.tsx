import { useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Cpu, Calendar, AlertTriangle, TrendingUp, Target, Database, Sparkles } from "lucide-react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { AIThinking } from "@/components/ui/ai-thinking";
import { decisionApi } from "@/lib/api";
import { useDatasetStore } from "@/store/dataset";

export default function ExecutivePage() {
  const { selectedId } = useDatasetStore();
  const execMut = useMutation({
    mutationFn: () => decisionApi.executive(selectedId!).then(r => r.data),
  });

  // See DecisionPage for why this reset is necessary -- mutations keep
  // their last result across dataset switches otherwise.
  useEffect(() => {
    execMut.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const advisory = execMut.data?.ai_advisory ?? null;

  if (!selectedId) return (
    <PageWrapper title="Executive Advisor" subtitle="Board-level decision intelligence">
      <EmptyState
        icon={Cpu}
        title="No dataset selected"
        description="Select a dataset from the header above to generate a board-level advisory: immediate actions, a 30/90-day plan, and long-term strategy."
        action={<Link to="/datasets"><Button size="sm" variant="outline" className="gap-1.5"><Database className="h-3.5 w-3.5" />Go to Datasets</Button></Link>}
      />
    </PageWrapper>
  );

  return (
    <PageWrapper title="Executive Advisor" subtitle="Board-level strategic intelligence and action plans">
      {execMut.isPending ? (
        <AIThinking label="Synthesizing a board-level advisory from your data…" />
      ) : !advisory ? (
        <div className="flex flex-col items-center justify-center py-24 gap-6">
          <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center">
            <Cpu className="h-8 w-8 text-primary" />
          </div>
          <div className="text-center">
            <h2 className="text-base font-semibold text-foreground">Board-Level Advisory</h2>
            <p className="text-sm text-muted-foreground mt-1 max-w-sm">Generate immediate actions, 30/90-day plans, and long-term strategy from your data.</p>
          </div>
          <Button onClick={() => execMut.mutate()} disabled={execMut.isPending} size="lg" className="gap-1.5">
            <Sparkles className="h-4 w-4" />
            Generate Executive Advisory
          </Button>
        </div>
      ) : (
        <div className="space-y-6 animate-fade-in">
          {/* Summary */}
          {advisory.executive_summary && (
            <div className="rounded-xl border border-primary/20 bg-primary/5 p-5">
              <p className="text-xs font-semibold text-primary uppercase tracking-widest mb-2">Executive Summary</p>
              <p className="text-sm text-foreground leading-relaxed">{advisory.executive_summary}</p>
              {advisory.expected_roi && (
                <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1.5">
                  <TrendingUp className="h-3 w-3 text-success" />Expected ROI: <span className="text-success font-medium">{advisory.expected_roi}</span>
                </p>
              )}
            </div>
          )}

          <div className="grid grid-cols-3 gap-4">
            {/* Immediate */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-destructive" />
                  <CardTitle>Immediate Actions</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                {(advisory.immediate_actions ?? []).length === 0 ? (
                  <p className="text-xs text-muted-foreground">None required.</p>
                ) : (
                  <div className="space-y-3">
                    {advisory.immediate_actions.map((a: any, i: number) => (
                      <div key={i} className="space-y-1">
                        <p className="text-xs font-semibold text-foreground">{a.action ?? a}</p>
                        {a.rationale && <p className="text-[10px] text-muted-foreground">{a.rationale}</p>}
                        {a.owner && <Badge variant="outline" className="text-[10px]">{a.owner}</Badge>}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 30-day */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-warning" />
                  <CardTitle>30-Day Plan</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {(advisory.plan_30_days ?? []).map((p: any, i: number) => (
                    <div key={i} className="space-y-0.5">
                      <p className="text-xs font-semibold text-foreground">{p.initiative ?? p}</p>
                      {p.expected_outcome && <p className="text-[10px] text-muted-foreground">{p.expected_outcome}</p>}
                    </div>
                  ))}
                  {(advisory.plan_30_days ?? []).length === 0 && <p className="text-xs text-muted-foreground">No 30-day initiatives.</p>}
                </div>
              </CardContent>
            </Card>

            {/* 90-day */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-primary" />
                  <CardTitle>90-Day Plan</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {(advisory.plan_90_days ?? []).map((p: any, i: number) => (
                    <div key={i} className="space-y-0.5">
                      <p className="text-xs font-semibold text-foreground">{p.initiative ?? p}</p>
                      {p.expected_outcome && <p className="text-[10px] text-muted-foreground">{p.expected_outcome}</p>}
                    </div>
                  ))}
                  {(advisory.plan_90_days ?? []).length === 0 && <p className="text-xs text-muted-foreground">No 90-day initiatives.</p>}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Risks + Strategy */}
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardHeader><CardTitle>Risk Register</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {(advisory.risks ?? []).map((r: any, i: number) => (
                    <div key={i} className="flex gap-2.5 p-2.5 rounded-lg border border-destructive/10 bg-destructive/5">
                      <AlertTriangle className="h-3.5 w-3.5 text-destructive mt-0.5 shrink-0" />
                      <div>
                        <p className="text-xs font-medium text-foreground">{r.risk ?? r}</p>
                        {r.mitigation && <p className="text-[10px] text-muted-foreground mt-0.5">→ {r.mitigation}</p>}
                      </div>
                      {r.likelihood && <Badge variant="destructive" className="ml-auto shrink-0 text-[10px]">{r.likelihood}</Badge>}
                    </div>
                  ))}
                  {(advisory.risks ?? []).length === 0 && <p className="text-xs text-muted-foreground">No risks identified.</p>}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Long-Term Strategy</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {(advisory.long_term_strategy ?? []).map((s: any, i: number) => (
                    <div key={i} className="space-y-1 border-b border-border pb-3 last:border-0 last:pb-0">
                      <p className="text-xs font-semibold text-foreground">{s.strategy ?? s}</p>
                      {s.horizon && <Badge variant="outline" className="text-[10px]">{s.horizon}</Badge>}
                      {s.expected_roi && <p className="text-[10px] text-success">{s.expected_roi}</p>}
                    </div>
                  ))}
                  {(advisory.long_term_strategy ?? []).length === 0 && <p className="text-xs text-muted-foreground">No strategy defined.</p>}
                </div>
              </CardContent>
            </Card>
          </div>

          <Button variant="outline" onClick={() => execMut.mutate()} className="gap-1.5">
            <Sparkles className="h-3.5 w-3.5" />
            Regenerate Advisory
          </Button>
        </div>
      )}
    </PageWrapper>
  );
}
