import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Brain, Target, GitBranch, AlertTriangle, Database } from "lucide-react";
import { motion } from "framer-motion";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BarChart } from "@/components/charts/BarChart";
import { ScoreGauge } from "@/components/charts/ScoreGauge";
import { PageLoading } from "@/components/ui/loading";
import { EmptyState } from "@/components/ui/empty-state";
import { rootCauseApi } from "@/lib/api";
import { useDatasetStore } from "@/store/dataset";

export default function RootCausePage() {
  const { selectedId } = useDatasetStore();
  const [target, setTarget] = useState("");

  const { data: rcData, isLoading } = useQuery({
    queryKey: ["root-cause", selectedId, target],
    queryFn: () => rootCauseApi.analyze(selectedId!, target || undefined).then(r => r.data),
    enabled: !!selectedId,
  });

  const { data: driversData } = useQuery({
    queryKey: ["drivers", selectedId, target],
    queryFn: () => rootCauseApi.drivers(selectedId!, target || undefined).then(r => r.data),
    enabled: !!selectedId,
  });

  if (!selectedId) return (
    <PageWrapper title="Root Cause Analysis" subtitle="Identify why business metrics behave as observed">
      <EmptyState
        icon={Brain}
        title="No dataset selected"
        description="Select a dataset from the header above — Kairos will automatically detect the key drivers behind its metrics."
        action={<Link to="/datasets"><Button size="sm" variant="outline" className="gap-1.5"><Database className="h-3.5 w-3.5" />Go to Datasets</Button></Link>}
      />
    </PageWrapper>
  );

  if (isLoading) return <PageLoading />;

  const topDrivers = driversData?.top_drivers ?? [];
  const whyChain = rcData?.why_chain ?? [];
  const anomalies = rcData?.anomaly_explanations ?? [];
  const conf = rcData?.overall_confidence ?? {};
  const summary = rcData?.summary ?? {};
  const driverChart = topDrivers.slice(0, 8).map((d: any) => ({
    col: d.column, importance: Number((d.importance * 100).toFixed(1))
  }));

  return (
    <PageWrapper title="Root Cause Analysis" subtitle={`Target: ${rcData?.target_column ?? "auto-detected"}`}>
      {/* Summary row */}
      <div className="grid grid-cols-4 gap-4">
        <div className="col-span-1 rounded-xl border border-border bg-card p-5 flex flex-col items-center gap-2">
          <ScoreGauge score={Math.round(conf.score ?? 0)} label="Analysis Confidence" size="lg" />
          <Badge variant={conf.band === "High" ? "success" : conf.band === "Medium" ? "warning" : "destructive"}>{conf.band ?? "—"}</Badge>
        </div>
        {[
          { label: "Target Column", value: summary.target ?? rcData?.target_column ?? "—", icon: Target },
          { label: "Drivers Found", value: summary.n_drivers_found ?? 0, icon: GitBranch },
          { label: "Anomaly Columns", value: summary.n_anomaly_columns ?? 0, icon: AlertTriangle },
        ].map((s, i) => {
          const Icon = s.icon;
          return (
            <motion.div key={s.label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 * i }}
              className="rounded-xl border border-border bg-card p-5">
              <div className="flex items-center gap-2 mb-2">
                <Icon className="h-4 w-4 text-primary" />
                <p className="text-xs text-muted-foreground">{s.label}</p>
              </div>
              <p className="text-2xl font-bold text-foreground tabular-nums">{String(s.value)}</p>
            </motion.div>
          );
        })}
      </div>

      <Tabs defaultValue="drivers">
        <TabsList>
          <TabsTrigger value="drivers">Driver Analysis</TabsTrigger>
          <TabsTrigger value="why">WHY Chain</TabsTrigger>
          <TabsTrigger value="anomalies">Anomalies {anomalies.length > 0 && `(${anomalies.length})`}</TabsTrigger>
        </TabsList>

        <TabsContent value="drivers">
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardHeader><CardTitle>Feature Importance</CardTitle></CardHeader>
              <CardContent>
                {driverChart.length === 0 ? <p className="text-xs text-muted-foreground">No drivers found.</p>
                  : <BarChart data={driverChart} xKey="col" yKey="importance" color="#3b82f6" height={220}
                      colorFn={(v) => v > 40 ? "#22c55e" : v > 20 ? "#f59e0b" : "#3b82f6"} />}
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Top Drivers</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {topDrivers.slice(0, 8).map((d: any, i: number) => (
                    <div key={d.column} className="flex items-center gap-3">
                      <span className="text-[10px] text-muted-foreground w-4 tabular-nums">{i + 1}</span>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-foreground">{d.column}</span>
                          <span className="text-xs text-muted-foreground tabular-nums">{(d.importance * 100).toFixed(1)}%</span>
                        </div>
                        <div className="h-1 bg-secondary rounded-full overflow-hidden">
                          <motion.div className={`h-full rounded-full ${d.direction === "positive" ? "bg-success" : "bg-destructive"}`}
                            initial={{ width: 0 }} animate={{ width: `${d.contribution_pct ?? d.importance * 100}%` }}
                            transition={{ delay: i * 0.05, duration: 0.6 }} />
                        </div>
                      </div>
                      <Badge variant={d.direction === "positive" ? "success" : "destructive"}>{d.direction}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="why">
          <Card>
            <CardHeader><CardTitle>Multi-Level WHY Chain</CardTitle></CardHeader>
            <CardContent>
              {whyChain.length === 0 ? <p className="text-xs text-muted-foreground">No WHY chain available.</p> : (
                <div className="relative">
                  {whyChain.map((step: any, i: number) => (
                    <motion.div key={i} initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                      className="flex gap-4 pb-6 last:pb-0">
                      <div className="flex flex-col items-center">
                        <div className="h-7 w-7 rounded-full bg-primary flex items-center justify-center text-[10px] font-bold text-primary-foreground shrink-0">
                          {step.level}
                        </div>
                        {i < whyChain.length - 1 && <div className="flex-1 w-px bg-border mt-1" />}
                      </div>
                      <div className="pt-1 pb-4">
                        <p className="text-xs font-semibold text-primary mb-1">{step.question}</p>
                        <p className="text-xs text-muted-foreground leading-relaxed">{step.answer}</p>
                        {step.confidence && (
                          <Badge variant="outline" className="mt-2">{step.confidence} confidence</Badge>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="anomalies">
          <Card>
            <CardHeader><CardTitle>Anomaly Explanations</CardTitle></CardHeader>
            <CardContent>
              {anomalies.length === 0 ? <p className="text-xs text-muted-foreground">No anomalies detected.</p> : (
                <div className="space-y-3">
                  {anomalies.map((a: any, i: number) => (
                    <div key={i} className="p-4 rounded-xl border border-warning/20 bg-warning/5 space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold text-foreground">{a.column}</p>
                        <Badge variant="warning">{a.outlier_count} outliers ({a.outlier_pct}%)</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">{a.business_impact}</p>
                      <div className="space-y-1">
                        {a.possible_causes?.slice(0, 2).map((c: string, j: number) => (
                          <p key={j} className="text-[10px] text-muted-foreground flex gap-1.5">
                            <span className="text-warning">•</span>{c}
                          </p>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </PageWrapper>
  );
}
