import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Lightbulb, TrendingUp, AlertTriangle, CheckCircle2, RotateCw, Database } from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScoreGauge } from "@/components/charts/ScoreGauge";
import { EmptyState } from "@/components/ui/empty-state";
import { AIThinking } from "@/components/ui/ai-thinking";
import { AITypingText } from "@/components/ui/ai-typing-text";
import { decisionApi } from "@/lib/api";
import { useDatasetStore } from "@/store/dataset";
import { priorityColor } from "@/lib/utils";

const catColors: Record<string, string> = {
  financial: "text-success", sales: "text-primary", operations: "text-warning",
  customer: "text-blue-400", executive: "text-purple-400", hr: "text-pink-400",
  marketing: "text-orange-400", supply_chain: "text-cyan-400",
};

export default function DecisionPage() {
  const { selectedId } = useDatasetStore();
  const [tab, setTab] = useState("all");

  // Auto-generates as soon as a dataset is selected -- no "Run Analysis"
  // button. useQuery (rather than useMutation) is what makes this
  // reactive to dataset switching for free: a new selectedId is a new
  // queryKey, so the previous dataset's recommendations never linger
  // and a fresh analysis kicks off automatically.
  const { data: result, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["decision-analyze", selectedId],
    queryFn: () => decisionApi.analyze(selectedId!).then(r => r.data),
    enabled: !!selectedId,
    staleTime: 60_000,
  });

  if (!selectedId) return (
    <PageWrapper title="Decision Advisor" subtitle="AI-powered prescriptive recommendations">
      <EmptyState
        icon={Lightbulb}
        title="No dataset selected"
        description="Select a dataset from the header above — recommendations generate automatically, no extra steps needed."
        action={<Link to="/datasets"><Button size="sm" variant="outline" className="gap-1.5"><Database className="h-3.5 w-3.5" />Go to Datasets</Button></Link>}
      />
    </PageWrapper>
  );

  if (isLoading) return (
    <PageWrapper title="Decision Advisor" subtitle="AI-powered prescriptive intelligence">
      <AIThinking label="Combining business rules and AI to generate recommendations…" />
    </PageWrapper>
  );

  if (isError || !result) return (
    <PageWrapper title="Decision Advisor" subtitle="AI-powered prescriptive intelligence">
      <EmptyState
        icon={AlertTriangle}
        tone="warning"
        title="Couldn't generate recommendations"
        description="Something went wrong analyzing this dataset. This usually resolves on retry."
        action={<Button size="sm" variant="outline" onClick={() => refetch()} className="gap-1.5"><RotateCw className="h-3.5 w-3.5" />Try again</Button>}
      />
    </PageWrapper>
  );

  const recs = result?.recommendations ?? [];
  const filtered = tab === "all" ? recs : recs.filter((r: any) => r.priority === tab);

  return (
    <PageWrapper title="Decision Advisor" subtitle="AI-powered prescriptive intelligence">
      <div className="space-y-6">
        {/* Summary */}
        {result.executive_summary && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-xl border border-primary/20 bg-primary/5 p-4">
            <p className="text-xs font-semibold text-primary uppercase tracking-widest mb-1.5">Executive Summary</p>
            <p className="text-sm text-foreground leading-relaxed">
              <AITypingText text={result.executive_summary} />
            </p>
          </motion.div>
        )}

        {recs.length === 0 ? (
          <EmptyState
            icon={CheckCircle2}
            title="No recommendations for this dataset yet"
            description="Nothing urgent was detected, or this dataset doesn't have enough signal for prescriptive analysis. Try a dataset with more rows or historical detail."
          />
        ) : (
          <>
            {/* Stats */}
            <div className="grid grid-cols-4 gap-4">
              <div className="rounded-xl border border-border bg-card p-4 text-center">
                <p className="text-2xl font-bold text-foreground">{recs.length}</p>
                <p className="text-xs text-muted-foreground mt-0.5">Recommendations</p>
              </div>
              {["high", "medium", "low"].map((p) => {
                const count = recs.filter((r: any) => r.priority === p).length;
                return (
                  <div key={p} className="rounded-xl border border-border bg-card p-4 text-center">
                    <p className="text-2xl font-bold text-foreground">{count}</p>
                    <p className={`text-xs mt-0.5 capitalize font-medium ${p === "high" ? "text-destructive" : p === "medium" ? "text-warning" : "text-muted-foreground"}`}>{p} priority</p>
                  </div>
                );
              })}
            </div>

            {/* Recommendations */}
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="all">All ({recs.length})</TabsTrigger>
                <TabsTrigger value="high">High</TabsTrigger>
                <TabsTrigger value="medium">Medium</TabsTrigger>
                <TabsTrigger value="low">Low</TabsTrigger>
              </TabsList>
              <TabsContent value={tab}>
                <div className="space-y-3">
                  {filtered.map((rec: any, i: number) => (
                    <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
                      whileHover={{ y: -2 }}
                      className="rounded-xl border border-border bg-card p-5 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all">
                      <div className="flex items-start gap-4">
                        <ScoreGauge score={Math.round(rec.overall_score ?? 50)} size="sm" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2 mb-1">
                            <p className="text-sm font-semibold text-foreground">{rec.title}</p>
                            <div className="flex items-center gap-1.5 shrink-0">
                              <Badge className={priorityColor(rec.priority)}>{rec.priority}</Badge>
                              <Badge variant="outline" className={catColors[rec.category] ?? "text-muted-foreground"}>{rec.category}</Badge>
                            </div>
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed mb-3">{rec.description}</p>
                          <div className="grid grid-cols-3 gap-2 text-[10px]">
                            {[
                              { label: "ROI Score", value: rec.roi_score?.toFixed(0), icon: TrendingUp },
                              { label: "Effort", value: rec.implementation_difficulty ?? "—", icon: AlertTriangle },
                              { label: "Timeline", value: rec.timeline ?? "—", icon: CheckCircle2 },
                            ].map((m) => {
                              const Icon = m.icon;
                              return (
                                <div key={m.label} className="flex items-center gap-1 text-muted-foreground">
                                  <Icon className="h-3 w-3" />
                                  <span>{m.label}: <span className="text-foreground font-medium">{m.value}</span></span>
                                </div>
                              );
                            })}
                          </div>
                          {rec.business_impact && (
                            <p className="text-[10px] text-muted-foreground mt-2 border-t border-border pt-2">{rec.business_impact}</p>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                  {filtered.length === 0 && (
                    <p className="text-xs text-muted-foreground text-center py-8">No {tab !== "all" ? tab + " priority" : ""} recommendations.</p>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </>
        )}

        <Button variant="outline" onClick={() => refetch()} disabled={isFetching} className="gap-1.5">
          <RotateCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          {isFetching ? "Refreshing…" : "Refresh Analysis"}
        </Button>
      </div>
    </PageWrapper>
  );
}
