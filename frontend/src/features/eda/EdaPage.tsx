import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { BarChart3, AlertTriangle, CheckCircle2, TrendingUp } from "lucide-react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScoreGauge } from "@/components/charts/ScoreGauge";
import { BarChart } from "@/components/charts/BarChart";
import { PageLoading } from "@/components/ui/loading";
import { EmptyState } from "@/components/ui/empty-state";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { Database } from "lucide-react";
import { edaApi } from "@/lib/api";
import { useDatasetStore } from "@/store/dataset";

export default function EdaPage() {
  const { selectedId } = useDatasetStore();

  const { data: quality, isLoading: qLoading } = useQuery({
    queryKey: ["eda-quality", selectedId],
    queryFn: () => edaApi.quality(selectedId!).then(r => r.data),
    enabled: !!selectedId,
  });

  const { data: summary } = useQuery({
    queryKey: ["eda-summary", selectedId],
    queryFn: () => edaApi.summary(selectedId!).then(r => r.data),
    enabled: !!selectedId,
  });

  const { data: outliers } = useQuery({
    queryKey: ["eda-outliers", selectedId],
    queryFn: () => edaApi.outliers(selectedId!).then(r => r.data),
    enabled: !!selectedId,
  });

  const { data: correlation } = useQuery({
    queryKey: ["eda-correlation", selectedId],
    queryFn: () => edaApi.correlation(selectedId!).then(r => r.data),
    enabled: !!selectedId,
  });

  const { data: insights } = useQuery({
    queryKey: ["eda-insights", selectedId],
    queryFn: () => edaApi.insights(selectedId!).then(r => r.data),
    enabled: !!selectedId,
  });

  const { data: missing } = useQuery({
    queryKey: ["eda-missing", selectedId],
    queryFn: () => edaApi.summary(selectedId!).then(r => r.data),
    enabled: !!selectedId,
  });

  if (!selectedId) return (
    <PageWrapper title="EDA" subtitle="Exploratory Data Analysis">
      <EmptyState
        icon={BarChart3}
        title="No dataset selected"
        description="Select a dataset from the header above to run exploratory analysis — quality scores, outliers, correlations, and more, generated automatically."
        action={<Link to="/datasets"><Button size="sm" variant="outline" className="gap-1.5"><Database className="h-3.5 w-3.5" />Go to Datasets</Button></Link>}
      />
    </PageWrapper>
  );

  if (qLoading) return <PageLoading />;

  const qScore = quality?.quality_score ?? 0;
  const qMetrics = quality?.metrics ?? {};

  const corrPairs = correlation?.highly_correlated_pairs ?? [];
  const outlierCols = outliers?.column_names_with_outliers ?? [];
  const insightList = insights?.insights ?? [];

  const missingData = Object.entries(summary?.missing_values ?? {})
    .map(([col, count]) => ({ col, count: Number(count) }))
    .filter(d => d.count > 0)
    .slice(0, 10);

  return (
    <PageWrapper title="Exploratory Data Analysis" subtitle="Automated statistical analysis and data quality assessment">
      {/* Quality overview */}
      <div className="grid grid-cols-4 gap-4">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
          className="rounded-xl border border-border bg-card p-5 flex flex-col items-center gap-2">
          <ScoreGauge score={Math.round(qScore)} label="Quality Score" size="lg" />
          <Badge variant={qScore >= 75 ? "success" : qScore >= 50 ? "warning" : "destructive"}>
            {qScore >= 75 ? "Good" : qScore >= 50 ? "Fair" : "Poor"}
          </Badge>
        </motion.div>
        {[
          { label: "Completeness", value: qMetrics.completeness ?? 0 },
          { label: "Consistency", value: qMetrics.consistency_score ?? 0 },
          { label: "Uniqueness", value: qMetrics.uniqueness_score ?? 0 },
        ].map((m, i) => (
          <motion.div key={m.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 * (i + 1) }}
            className="rounded-xl border border-border bg-card p-5">
            <p className="text-xs text-muted-foreground mb-2">{m.label}</p>
            <p className="text-2xl font-bold text-foreground tabular-nums">{Number(m.value).toFixed(1)}%</p>
            <div className="mt-3 h-1.5 bg-secondary rounded-full overflow-hidden">
              <motion.div className="h-full bg-primary rounded-full"
                initial={{ width: 0 }} animate={{ width: `${m.value}%` }} transition={{ delay: 0.3, duration: 0.8 }} />
            </div>
          </motion.div>
        ))}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="insights">
        <TabsList>
          <TabsTrigger value="insights">Insights</TabsTrigger>
          <TabsTrigger value="outliers">Outliers</TabsTrigger>
          <TabsTrigger value="correlation">Correlation</TabsTrigger>
          <TabsTrigger value="missing">Missing Values</TabsTrigger>
        </TabsList>

        <TabsContent value="insights">
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardHeader><CardTitle>Auto-Generated Insights</CardTitle></CardHeader>
              <CardContent>
                {insightList.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No insights available.</p>
                ) : (
                  <div className="space-y-2">
                    {insightList.map((ins: string, i: number) => (
                      <div key={i} className="flex gap-2.5 p-2.5 rounded-lg bg-muted/50">
                        <TrendingUp className="h-3.5 w-3.5 text-primary mt-0.5 shrink-0" />
                        <p className="text-xs text-muted-foreground leading-relaxed">{ins}</p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Dataset Summary</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(summary ?? {}).filter(([k]) => !["columns", "missing_values"].includes(k)).slice(0, 8).map(([k, v]) => (
                    <div key={k} className="flex justify-between py-1.5 border-b border-border last:border-0">
                      <span className="text-xs text-muted-foreground">{k.replace(/_/g, " ")}</span>
                      <span className="text-xs font-medium text-foreground tabular-nums">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="outliers">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Outlier Detection</CardTitle>
                <Badge variant={outliers?.total_outliers > 0 ? "warning" : "success"}>
                  {outliers?.total_outliers ?? 0} outliers
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              {outlierCols.length === 0 ? (
                <Alert variant="success" title="No significant outliers detected">
                  All columns are within expected ranges.
                </Alert>
              ) : (
                <div className="space-y-3">
                  {outlierCols.map((col: string) => {
                    const detail = outliers?.columns?.[col] ?? {};
                    return (
                      <div key={col} className="flex items-center gap-3 p-3 rounded-lg border border-warning/20 bg-warning/5">
                        <AlertTriangle className="h-4 w-4 text-warning shrink-0" />
                        <div className="flex-1">
                          <p className="text-xs font-medium text-foreground">{col}</p>
                          <p className="text-[10px] text-muted-foreground">
                            {detail.outlier_count} outliers · bounds [{Number(detail.lower_bound).toFixed(2)}, {Number(detail.upper_bound).toFixed(2)}]
                          </p>
                        </div>
                        <Badge variant="warning">{detail.outlier_percentage?.toFixed(1)}%</Badge>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="correlation">
          <Card>
            <CardHeader><CardTitle>Highly Correlated Variables</CardTitle></CardHeader>
            <CardContent>
              {corrPairs.length === 0 ? (
                <p className="text-xs text-muted-foreground">No highly correlated pairs found.</p>
              ) : (
                <div className="space-y-2">
                  {corrPairs.slice(0, 10).map((p: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-muted/50">
                      <div className="flex-1">
                        <span className="text-xs font-medium text-foreground">{p.column_1}</span>
                        <span className="text-xs text-muted-foreground mx-2">↔</span>
                        <span className="text-xs font-medium text-foreground">{p.column_2}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-20 bg-secondary rounded-full overflow-hidden">
                          <div className="h-full bg-primary rounded-full" style={{ width: `${Math.abs(p.correlation) * 100}%` }} />
                        </div>
                        <span className="text-xs font-mono text-primary w-12 text-right">{Number(p.correlation).toFixed(3)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="missing">
          <Card>
            <CardHeader><CardTitle>Missing Value Analysis</CardTitle></CardHeader>
            <CardContent>
              {missingData.length === 0 ? (
                <Alert variant="success" title="No missing values">
                  Dataset is complete with no missing values.
                </Alert>
              ) : (
                <BarChart data={missingData} xKey="col" yKey="count" color="#f59e0b" height={200} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </PageWrapper>
  );
}
