import { useState, useEffect, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Zap, Plus, Trash2, BarChart3, Database, Sparkles, ChevronDown, ChevronUp, Wand2 } from "lucide-react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BarChart } from "@/components/charts/BarChart";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { PageLoading } from "@/components/ui/loading";
import { EmptyState } from "@/components/ui/empty-state";
import { VariableSliderCard } from "./VariableSliderCard";
import { simulationApi } from "@/lib/api";
import { useDatasetStore } from "@/store/dataset";
import { humanize } from "@/lib/utils";

export default function SimulationPage() {
  const { selectedId } = useDatasetStore();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [variable, setVariable] = useState("");
  const [newValue, setNewValue] = useState("");
  const [scenarios, setScenarios] = useState<Array<{ name: string; vars: Record<string, string> }>>([]);

  const { data: trainData, isLoading } = useQuery({
    queryKey: ["sim-train", selectedId],
    queryFn: () => simulationApi.train(selectedId!).then(r => r.data),
    enabled: !!selectedId,
  });

  const { data: sensData } = useQuery({
    queryKey: ["sim-sensitivity", selectedId],
    queryFn: () => simulationApi.sensitivity(selectedId!).then(r => r.data),
    enabled: !!selectedId,
  });

  const singleMut = useMutation({
    mutationFn: () => simulationApi.single(selectedId!, variable, Number(newValue)).then(r => r.data),
  });

  const compareMut = useMutation({
    mutationFn: () => simulationApi.compare(selectedId!, scenarios.map(s => ({
      name: s.name,
      variables: Object.fromEntries(Object.entries(s.vars).map(([k, v]) => [k, Number(v)])),
    }))).then(r => r.data),
  });

  useEffect(() => {
    singleMut.reset();
    compareMut.reset();
    setVariable("");
    setNewValue("");
    setScenarios([]);
    setAdvancedOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const features: string[] = trainData?.feature_columns ?? [];
  const cmp = trainData?.model_comparison ?? {};
  const featureStats = trainData?.feature_stats ?? {};
  const sensRanking = sensData?.sensitivity_ranking ?? [];

  // The whole point: don't make the user pick a column cold. Surface
  // the variables sensitivity analysis already identified as most
  // influential, falling back to the first few feature columns only if
  // sensitivity data isn't available yet.
  const topVariables = useMemo(() => {
    const ranked = sensRanking.map((r: any) => r.column).filter((c: string) => featureStats[c]);
    const source = ranked.length > 0 ? ranked : features;
    return source.slice(0, 3);
  }, [sensRanking, features, featureStats]);

  const targetColumn = trainData?.target_column ?? "";

  // Quick scenario suggestions built from the same sensitivity data --
  // zero typing required to get a starting comparison.
  const suggestScenarios = () => {
    const top = sensRanking[0]?.column ?? features[0];
    if (!top || !featureStats[top]) return;
    const mean = featureStats[top].mean;
    const presets = [
      { name: "Conservative", pct: -0.15 },
      { name: "Growth", pct: 0.15 },
      { name: "Aggressive", pct: 0.3 },
    ];
    setScenarios(presets.map((p) => ({
      name: p.name,
      vars: { [top]: (mean * (1 + p.pct)).toFixed(2) },
    })));
  };

  if (!selectedId) return (
    <PageWrapper title="What-If Simulation" subtitle="Explore business scenarios instantly">
      <EmptyState
        icon={Zap}
        title="No dataset selected"
        description="Select a dataset from the header above to start simulating scenarios."
        action={<Link to="/datasets"><Button size="sm" variant="outline" className="gap-1.5"><Database className="h-3.5 w-3.5" />Go to Datasets</Button></Link>}
      />
    </PageWrapper>
  );

  if (isLoading) return <PageLoading />;

  if (features.length === 0) {
    return (
      <PageWrapper title="What-If Simulation" subtitle="Explore business scenarios instantly">
        <EmptyState
          icon={Zap}
          tone="warning"
          title="Not enough structure to simulate"
          description="This dataset doesn't have enough numeric variables to build a predictive model. Try a dataset with more measurable columns."
        />
      </PageWrapper>
    );
  }

  return (
    <PageWrapper
      title="What-If Simulation"
      subtitle={`Predicting ${humanize(targetColumn)} · ${cmp.test_r2 != null ? `${Math.round(cmp.test_r2 * 100)}% model fit` : ""}`}
    >
      <Tabs defaultValue="single">
        <TabsList>
          <TabsTrigger value="single">Try a Scenario</TabsTrigger>
          <TabsTrigger value="sensitivity">What Matters Most</TabsTrigger>
          <TabsTrigger value="compare">Compare Scenarios</TabsTrigger>
        </TabsList>

        {/* ── Try a Scenario: sliders on auto-suggested variables ── */}
        <TabsContent value="single">
          <div className="space-y-4">
            <p className="text-xs text-muted-foreground">
              These are the variables that influence <span className="text-foreground font-medium">{humanize(targetColumn)}</span> the
              most. Drag a slider to see the predicted effect — no need to know column names or type numbers.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {topVariables.map((col: string, i: number) => (
                <VariableSliderCard
                  key={col}
                  datasetId={selectedId}
                  column={col}
                  targetColumn={targetColumn}
                  mean={featureStats[col]?.mean ?? 0}
                  min={featureStats[col]?.min ?? 0}
                  max={featureStats[col]?.max ?? 1}
                  index={i}
                />
              ))}
            </div>

            {/* Advanced: manual variable + value, for power users */}
            <div className="pt-2">
              <button
                onClick={() => setAdvancedOpen((o) => !o)}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {advancedOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                Advanced: pick any variable manually
              </button>
              {advancedOpen && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-3">
                  <Card>
                    <CardContent className="pt-5 grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="space-y-3">
                        <div className="space-y-1.5">
                          <label className="text-xs text-muted-foreground font-medium">Variable</label>
                          <select
                            value={variable}
                            onChange={(e) => setVariable(e.target.value)}
                            className="h-9 w-full rounded-lg border border-input bg-muted px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                          >
                            <option value="">Select a variable…</option>
                            {features.map((f) => <option key={f} value={f}>{humanize(f)}</option>)}
                          </select>
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-xs text-muted-foreground font-medium">New Value</label>
                          <Input type="number" placeholder="e.g. 150" value={newValue} onChange={(e) => setNewValue(e.target.value)} />
                        </div>
                        <Button className="w-full gap-1.5" size="sm" disabled={!variable || !newValue || singleMut.isPending} onClick={() => singleMut.mutate()}>
                          <Sparkles className="h-3.5 w-3.5" />
                          {singleMut.isPending ? "Predicting…" : "Run"}
                        </Button>
                      </div>
                      <div className="md:col-span-2">
                        {singleMut.data && (
                          <div className="space-y-2 text-xs">
                            <p className="text-foreground">
                              Predicted {humanize(targetColumn)}: <span className="font-semibold">{singleMut.data.scenario_prediction?.toFixed(2)}</span>{" "}
                              ({singleMut.data.delta_pct >= 0 ? "+" : ""}{singleMut.data.delta_pct?.toFixed(1)}%)
                            </p>
                            {singleMut.data.recommendations?.map((r: string, i: number) => (
                              <p key={i} className="text-muted-foreground flex gap-1.5"><span className="text-primary">•</span>{r}</p>
                            ))}
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* ── Sensitivity ──────────────────────────────────────── */}
        <TabsContent value="sensitivity">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Sensitivity Ranking</CardTitle>
                <CardDescription>Which variables move the outcome the most.</CardDescription>
              </CardHeader>
              <CardContent>
                {sensRanking.length === 0 ? (
                  <EmptyState icon={BarChart3} title="Not enough data" description="Sensitivity analysis needs more variables to compare." />
                ) : (
                  <BarChart
                    data={sensRanking.slice(0, 8).map((r: any) => ({ col: humanize(r.column), score: Number(r.relative_sensitivity) }))}
                    xKey="col" yKey="score" color="#f59e0b" height={240}
                    colorFn={(v) => v > 70 ? "#ef4444" : v > 40 ? "#f59e0b" : "#22c55e"}
                  />
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Most Influential Variables</CardTitle>
                <CardDescription>Ranked by how much they change the predicted outcome.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {sensRanking.slice(0, 8).map((r: any, i: number) => (
                    <motion.div key={r.column} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }}
                      className="flex items-center gap-3">
                      <span className="text-[10px] text-muted-foreground w-4 tabular-nums">{r.rank}</span>
                      <div className="flex-1">
                        <div className="flex justify-between mb-1">
                          <span className="text-xs font-medium text-foreground">{humanize(r.column)}</span>
                          <span className="text-[10px] font-mono text-muted-foreground">{r.relative_sensitivity?.toFixed(1)}</span>
                        </div>
                        <div className="h-1 bg-secondary rounded-full">
                          <motion.div className={`h-full rounded-full ${r.direction === "positive" ? "bg-success" : "bg-destructive"}`}
                            initial={{ width: 0 }} animate={{ width: `${r.relative_sensitivity}%` }} transition={{ delay: i * 0.05, duration: 0.6 }} />
                        </div>
                      </div>
                      <Badge variant={r.direction === "positive" ? "success" : "destructive"} className="text-[10px]">{r.direction}</Badge>
                    </motion.div>
                  ))}
                  {sensRanking.length === 0 && (
                    <EmptyState icon={Sparkles} title="No ranking available" description="Try a dataset with more numeric variables." />
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ── Compare ──────────────────────────────────────────── */}
        <TabsContent value="compare">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Scenarios</CardTitle>
                  <Button size="sm" variant="outline" onClick={() => setScenarios((s) => [...s, { name: `Scenario ${s.length + 1}`, vars: {} }])}>
                    <Plus className="h-3 w-3 mr-1" />Add
                  </Button>
                </div>
                <CardDescription>Compare a few named scenarios side by side.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {scenarios.length === 0 && (
                  <Button variant="outline" className="w-full gap-1.5" size="sm" onClick={suggestScenarios}>
                    <Wand2 className="h-3.5 w-3.5" />
                    Suggest scenarios for me
                  </Button>
                )}
                {scenarios.map((s, si) => (
                  <div key={si} className="rounded-xl border border-border p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <Input value={s.name} onChange={(e) => setScenarios((prev) => prev.map((p, i) => (i === si ? { ...p, name: e.target.value } : p)))} className="h-7 text-xs w-36" />
                      <Button variant="ghost" size="icon-sm" onClick={() => setScenarios((s) => s.filter((_, i) => i !== si))}>
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                    {(topVariables.length > 0 ? topVariables : features.slice(0, 3)).map((f: string) => (
                      <div key={f} className="flex items-center gap-2">
                        <span className="text-[10px] text-muted-foreground w-20 truncate" title={f}>{humanize(f)}</span>
                        <Input type="number" placeholder="value" className="h-6 text-[11px]"
                          value={s.vars[f] ?? ""}
                          onChange={(e) => setScenarios((prev) => prev.map((p, i) => (i === si ? { ...p, vars: { ...p.vars, [f]: e.target.value } } : p)))} />
                      </div>
                    ))}
                  </div>
                ))}
                {scenarios.length > 0 && (
                  <Button className="w-full gap-1.5" onClick={() => compareMut.mutate()} disabled={compareMut.isPending}>
                    <Sparkles className="h-3.5 w-3.5" />
                    {compareMut.isPending ? "Comparing…" : "Compare Scenarios"}
                  </Button>
                )}
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>Comparison Results</CardTitle></CardHeader>
              <CardContent>
                {!compareMut.data ? (
                  <EmptyState icon={BarChart3} title="No comparison yet" description='Click "Suggest scenarios for me" or add your own on the left, then compare them.' />
                ) : (
                  <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                    <div className="flex items-center gap-3 flex-wrap">
                      <Badge variant="success">Best: {compareMut.data.best_scenario}</Badge>
                      <Badge variant="destructive">Worst: {compareMut.data.worst_scenario}</Badge>
                    </div>
                    <BarChart
                      data={[
                        { label: "Baseline", value: compareMut.data.baseline_prediction },
                        ...((compareMut.data.results ?? []).filter((r: any) => r.prediction != null).map((r: any) => ({ label: r.name, value: r.prediction }))),
                      ]}
                      xKey="label" yKey="value" height={200}
                      colorFn={(v) => (v > compareMut.data.baseline_prediction ? "#22c55e" : "#ef4444")}
                    />
                    <div className="space-y-2">
                      {(compareMut.data.results ?? []).map((r: any) => (
                        <div key={r.name} className="flex items-center gap-3 p-2.5 rounded-lg bg-muted/50">
                          <Badge variant={r.rank === 1 ? "success" : "outline"}>#{r.rank}</Badge>
                          <span className="text-xs font-medium text-foreground flex-1">{r.name}</span>
                          <span className="text-xs font-mono text-foreground">{r.prediction?.toFixed(4)}</span>
                          <span className={`text-xs font-mono ${r.delta_pct >= 0 ? "text-success" : "text-destructive"}`}>
                            {r.delta_pct >= 0 ? "+" : ""}{r.delta_pct?.toFixed(1)}%
                          </span>
                        </div>
                      ))}
                    </div>
                    {compareMut.data.recommendations?.length > 0 && (
                      <div className="border-t border-border pt-3 space-y-1.5">
                        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">What This Means</p>
                        {compareMut.data.recommendations.map((r: string, i: number) => (
                          <p key={i} className="text-xs text-muted-foreground flex gap-2"><span className="text-primary">•</span>{r}</p>
                        ))}
                      </div>
                    )}
                  </motion.div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </PageWrapper>
  );
}
