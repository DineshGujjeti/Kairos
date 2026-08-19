import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Database, TrendingUp, Brain, Zap, ArrowRight, Activity, BarChart3, Lightbulb } from "lucide-react";
import { Link } from "react-router-dom";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { MetricCard } from "@/components/ui/metric-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScoreGauge } from "@/components/charts/ScoreGauge";
import { AreaChart } from "@/components/charts/AreaChart";
import { PageLoading } from "@/components/ui/loading";
import { EmptyState } from "@/components/ui/empty-state";
import { datasetsApi, kpiApi, aiApi } from "@/lib/api";
import { useDatasetStore } from "@/store/dataset";
import { useAuthStore } from "@/store/auth";
import { fmtDate, truncate } from "@/lib/utils";

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { selectedId, setDatasets } = useDatasetStore();

  const { data: datasets = [], isLoading } = useQuery({
  queryKey: ["datasets"],
  queryFn: async () => {
    const r = await datasetsApi.list();

    const items = Array.isArray(r.data.items)
      ? r.data.items
      : [];

    setDatasets(items);

    return items;
  },
});
  const activeId = selectedId ?? datasets[0]?.id;

  const { data: kpiData } = useQuery({
    queryKey: ["kpi-overview", activeId],
    queryFn: () => kpiApi.overview(activeId!).then((r) => r.data),
    enabled: !!activeId,
  });

  const { data: aiHealth } = useQuery({
    queryKey: ["ai-health"],
    queryFn: () => aiApi.health().then((r) => r.data),
  });

  if (isLoading) return <PageLoading />;

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  const quickActions = [
    { label: "Upload Dataset", href: "/datasets", icon: Database, color: "text-primary" },
    { label: "Run EDA", href: "/eda", icon: BarChart3, color: "text-success" },
    { label: "KPI Dashboard", href: "/kpi", icon: TrendingUp, color: "text-warning" },
    { label: "Forecast", href: "/forecasting", icon: Activity, color: "text-primary" },
    { label: "Root Cause", href: "/root-cause", icon: Brain, color: "text-destructive" },
    { label: "Simulation", href: "/simulation", icon: Zap, color: "text-warning" },
    { label: "Decisions", href: "/decision", icon: Lightbulb, color: "text-success" },
  ];

  return (
    <PageWrapper title="Overview" subtitle={`${greeting}, ${user?.full_name?.split(" ")[0] ?? "there"}`}>
      {/* Hero row */}
      <div className="grid grid-cols-3 gap-4">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          className="col-span-2 rounded-xl border border-border bg-card p-5 flex items-center gap-6">
          <div className="flex-1">
            <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Platform Status</p>
            <h2 className="text-lg font-semibold text-foreground">Kairos Decision Intelligence</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {datasets.length} dataset{datasets.length !== 1 ? "s" : ""} loaded
              {aiHealth?.available ? " · AI insights enabled" : " · Configure GEMINI_API_KEY for AI insights"}
            </p>
            <div className="flex items-center gap-2 mt-3">
              <Badge variant={aiHealth?.available ? "success" : "default"}>
                {aiHealth?.available ? "AI Active" : "AI Offline"}
              </Badge>
              <Badge variant="primary">{datasets.length} Datasets</Badge>
            </div>
          </div>
          <div className="shrink-0">
            <ScoreGauge score={datasets.length > 0 ? 82 : 20} label="Health" size="lg" />
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="rounded-xl border border-border bg-card p-5 flex flex-col gap-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Quick Actions</p>
          <div className="grid grid-cols-2 gap-2">
            {quickActions.slice(0, 6).map((a) => {
              const Icon = a.icon;
              return (
                <Link key={a.href} to={a.href}
                  className="flex flex-col items-center gap-1.5 p-2 rounded-lg hover:bg-accent transition-colors group">
                  <Icon className={`h-4 w-4 ${a.color}`} />
                  <span className="text-[10px] text-muted-foreground group-hover:text-foreground text-center leading-tight">{a.label}</span>
                </Link>
              );
            })}
          </div>
        </motion.div>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard title="Datasets" value={datasets.length} icon={Database} color="blue" index={0} />
        <MetricCard title="AI Status" value={aiHealth?.available ? "Active" : "Offline"} icon={Brain}
          color={aiHealth?.available ? "green" : "red"} index={1} />
        <MetricCard title="Total Rows" value={datasets.reduce((sum: number, d: any) => sum + (d.row_count ?? 0), 0).toLocaleString()} icon={Zap} color="amber" index={2} />
        <MetricCard title="Ready to Analyze" value={datasets.filter((d: any) => d.status === "valid").length} icon={Activity} color="green" index={3} />
      </div>

      {/* Datasets + Chart */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Recent Datasets</CardTitle>
              <Link to="/datasets">
                <Button variant="ghost" size="sm" className="gap-1 text-xs">View all <ArrowRight className="h-3 w-3" /></Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {datasets.length === 0 ? (
              <EmptyState icon={Database} title="No datasets yet" description="Upload a dataset to get started." action={
                <Link to="/datasets"><Button size="sm">Upload Dataset</Button></Link>
              } />
            ) : (
              <div className="space-y-2">
                {datasets.slice(0, 5).map((d: any) => (
                  <div key={d.id} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-accent transition-colors group">
                    <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <Database className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-foreground truncate">{truncate(d.name, 32)}</p>
                      <p className="text-[10px] text-muted-foreground">{d.dataset_type} · {fmtDate(d.created_at)}</p>
                    </div>
                    <Badge variant={d.status === "ready" ? "success" : "default"}>{d.status}</Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>KPI Overview</CardTitle>
          </CardHeader>
          <CardContent>
            {!activeId ? (
              <EmptyState icon={TrendingUp} title="No dataset selected" description="Select a dataset to see KPIs." />
            ) : !kpiData ? (
              <div className="h-48 flex items-center justify-center">
                <p className="text-xs text-muted-foreground">Loading KPIs…</p>
              </div>
            ) : (
              <div className="space-y-3">
                {Object.entries(kpiData).slice(0, 4).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
                    <p className="text-xs text-muted-foreground">{k}</p>
                    <p className="text-xs font-semibold text-foreground tabular-nums">{String(v)}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Feature cards */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">Explore Your Data</p>
        <div className="grid grid-cols-4 gap-3">
          {[
            { title: "Root Cause Analysis", desc: "Find hidden drivers behind your metrics", href: "/root-cause", icon: Brain, badge: "AI-Powered" },
            { title: "What-If Simulation", desc: "Explore business scenarios instantly", href: "/simulation", icon: Zap, badge: "Interactive" },
            { title: "Decision Advisor", desc: "Get prioritized, scored recommendations", href: "/decision", icon: Lightbulb, badge: "AI-Powered" },
            { title: "Executive Advisor", desc: "Board-level strategy and action plans", href: "/executive", icon: TrendingUp, badge: "AI-Powered" },
          ].map((m, i) => {
            const Icon = m.icon;
            return (
              <motion.div key={m.href} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.05 }}>
                <Link to={m.href} className="block rounded-xl border border-border bg-card p-4 hover:border-primary/30 hover:bg-accent transition-all group">
                  <div className="flex items-start justify-between mb-3">
                    <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <Badge variant="outline">{m.badge}</Badge>
                  </div>
                  <p className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors">{m.title}</p>
                  <p className="text-[10px] text-muted-foreground mt-1 leading-relaxed">{m.desc}</p>
                </Link>
              </motion.div>
            );
          })}
        </div>
      </div>
    </PageWrapper>
  );
}
