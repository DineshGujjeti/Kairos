import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  TrendingUp, AlertTriangle, ArrowUpRight, ArrowDownRight, Minus,
  Sparkles, Database, ChevronDown, ChevronUp,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BarChart } from "@/components/charts/BarChart";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { PageLoading } from "@/components/ui/loading";
import { EmptyState } from "@/components/ui/empty-state";
import { kpiApi } from "@/lib/api";
import { useDatasetStore } from "@/store/dataset";
import { cn } from "@/lib/utils";

const SENTIMENT_STYLE: Record<string, { icon: string; ring: string; badge: "success" | "destructive" | "default" }> = {
  positive: { icon: "text-success", ring: "border-success/20 bg-success/[0.03]", badge: "success" },
  negative: { icon: "text-destructive", ring: "border-destructive/20 bg-destructive/[0.03]", badge: "destructive" },
  neutral: { icon: "text-muted-foreground", ring: "border-border", badge: "default" },
};

function DirectionIcon({ direction }: { direction: string }) {
  if (direction === "up") return <ArrowUpRight className="h-4 w-4" />;
  if (direction === "down") return <ArrowDownRight className="h-4 w-4" />;
  return <Minus className="h-4 w-4" />;
}

function SmartKpiCard({ card, index }: { card: any; index: number }) {
  const style = SENTIMENT_STYLE[card.sentiment] ?? SENTIMENT_STYLE.neutral;
  const isCurrency = card.formatted_value?.startsWith("$");
  const isPercent = card.formatted_value?.endsWith("%");
  const numericValue = Number(card.value);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.3 }}
      whileHover={{ y: -2 }}
      className={cn("rounded-xl border p-4 flex flex-col gap-2 relative overflow-hidden", style.ring)}
    >
      {card.is_notable && (
        <div className="absolute top-2.5 right-2.5">
          <Badge variant={style.badge} className="text-[9px] gap-1">
            <Sparkles className="h-2.5 w-2.5" /> Notable
          </Badge>
        </div>
      )}
      <p className="text-xs text-muted-foreground pr-16">{card.label}</p>
      <p className="text-2xl font-bold text-foreground tabular-nums">
        {isCurrency && "$"}
        <AnimatedNumber
          value={numericValue}
          decimals={isPercent || (Math.abs(numericValue) < 100 && !Number.isInteger(numericValue)) ? 1 : 0}
        />
        {isPercent && "%"}
      </p>
      {card.trend_available ? (
        <div className={cn("flex items-center gap-1 text-xs font-medium", style.icon)}>
          <DirectionIcon direction={card.direction} />
          <span>{card.change_pct >= 0 ? "+" : ""}{card.change_pct?.toFixed(1)}%</span>
        </div>
      ) : (
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Minus className="h-3.5 w-3.5" />
          <span>Not enough data for a trend</span>
        </div>
      )}
      <p className="text-[11px] text-muted-foreground leading-relaxed pt-1 border-t border-border/60 mt-1">
        {card.description}
      </p>
    </motion.div>
  );
}

export default function KpiPage() {
  const { selectedId } = useDatasetStore();
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const { data: smartData, isLoading } = useQuery({
    queryKey: ["kpi-smart-cards", selectedId],
    queryFn: () => kpiApi.smartCards(selectedId!, 6).then(r => r.data),
    enabled: !!selectedId,
  });

  const { data: metrics } = useQuery({
    queryKey: ["kpi-metrics", selectedId],
    queryFn: () => kpiApi.metrics(selectedId!).then(r => r.data),
    enabled: !!selectedId && advancedOpen,
  });

  const { data: alerts } = useQuery({
    queryKey: ["kpi-alerts", selectedId],
    queryFn: () => kpiApi.alerts(selectedId!).then(r => r.data),
    enabled: !!selectedId,
  });

  if (!selectedId) return (
    <PageWrapper title="KPI Analytics" subtitle="The metrics that actually matter, explained">
      <EmptyState
        icon={TrendingUp}
        title="No dataset selected"
        description="Select a dataset from the header above — Kairos automatically picks out the metrics worth tracking and explains what's happening with each one."
        action={<Link to="/datasets"><Button size="sm" variant="outline" className="gap-1.5"><Database className="h-3.5 w-3.5" />Go to Datasets</Button></Link>}
      />
    </PageWrapper>
  );

  if (isLoading) return <PageLoading />;

  const cards = smartData?.cards ?? [];
  const alertList = alerts?.alerts ?? [];
  const colMetrics = metrics?.columns ?? {};
  const cols = Object.keys(colMetrics).slice(0, 8);
  const barData = cols.map((c) => ({ col: c, mean: Number(colMetrics[c]?.mean ?? 0) }));

  return (
    <PageWrapper title="KPI Analytics" subtitle="The metrics that actually matter, explained">
      {!smartData?.has_measures ? (
        <EmptyState
          icon={TrendingUp}
          tone="warning"
          title="Not enough numeric data for KPIs"
          description="This dataset doesn't have measurable columns (like revenue, cost, or quantity) that Kairos can turn into KPI cards. Try a dataset with more numeric data."
        />
      ) : (
        <>
          {/* AI summary line */}
          {smartData.summary && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex items-center gap-2.5 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3"
            >
              <Sparkles className="h-4 w-4 text-primary shrink-0" />
              <p className="text-xs text-foreground">{smartData.summary}</p>
            </motion.div>
          )}

          {/* Smart KPI cards -- the hero content */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {cards.map((card: any, i: number) => (
              <SmartKpiCard key={card.key} card={card} index={i} />
            ))}
          </div>

          {!smartData.has_time_comparison && (
            <p className="text-[11px] text-muted-foreground text-center">
              No date column was found, so trends compare earlier vs. later records rather than calendar periods.
            </p>
          )}
        </>
      )}

      {/* Alerts -- always shown if present, regardless of card availability */}
      {alertList.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Alerts</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {alertList.map((a: any, i: number) => (
                <div key={i} className="flex gap-3 p-3 rounded-lg border border-warning/20 bg-warning/5">
                  <AlertTriangle className="h-4 w-4 text-warning mt-0.5 shrink-0" />
                  <div>
                    <p className="text-xs font-medium text-foreground">{a.title ?? a.type}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{a.message ?? a.description}</p>
                  </div>
                  <Badge variant="warning" className="ml-auto shrink-0">{a.severity ?? "medium"}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Advanced / raw stats -- collapsed by default, for power users */}
      <div>
        <button
          onClick={() => setAdvancedOpen((o) => !o)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {advancedOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          Advanced: raw column statistics
        </button>
        {advancedOpen && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-3">
            <Tabs defaultValue="table">
              <TabsList>
                <TabsTrigger value="table">Column Stats</TabsTrigger>
                <TabsTrigger value="chart">Mean by Column</TabsTrigger>
              </TabsList>
              <TabsContent value="table">
                <Card>
                  <CardContent className="pt-5">
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-border">
                            {["Column", "Count", "Sum", "Mean", "Min", "Max", "Std"].map((h) => (
                              <th key={h} className="pb-2 text-left text-muted-foreground font-medium pr-4">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          {cols.map((col) => {
                            const m = colMetrics[col] ?? {};
                            return (
                              <tr key={col} className="hover:bg-accent transition-colors">
                                <td className="py-2 pr-4 font-medium text-foreground">{col}</td>
                                {["count", "sum", "mean", "min", "max", "std"].map((k) => (
                                  <td key={k} className="py-2 pr-4 text-muted-foreground tabular-nums">
                                    {m[k] != null ? Number(m[k]).toLocaleString(undefined, { maximumFractionDigits: 2 }) : "—"}
                                  </td>
                                ))}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
              <TabsContent value="chart">
                <Card>
                  <CardContent className="pt-5">
                    {barData.length === 0 ? <p className="text-xs text-muted-foreground">No numeric columns.</p>
                      : <BarChart data={barData} xKey="col" yKey="mean" color="#3b82f6" height={240} />}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </motion.div>
        )}
      </div>
    </PageWrapper>
  );
}
