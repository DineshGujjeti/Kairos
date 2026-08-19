import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  LineChart, TrendingUp, TrendingDown, Minus, Info, Database, ArrowRight, Clock3,
} from "lucide-react";
import { Link } from "react-router-dom";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AreaChart } from "@/components/charts/AreaChart";
import { MetricCard } from "@/components/ui/metric-card";
import { PageLoading } from "@/components/ui/loading";
import { EmptyState } from "@/components/ui/empty-state";
import { ScoreGauge } from "@/components/charts/ScoreGauge";
import { forecastApi } from "@/lib/api";
import { useDatasetStore } from "@/store/dataset";

export default function ForecastPage() {
  const { selectedId } = useDatasetStore();
  const [periods, setPeriods] = useState(30);

  const { data: report, isLoading } = useQuery({
    queryKey: ["forecast-report", selectedId, periods],
    queryFn: () => forecastApi.report(selectedId!, periods).then(r => r.data),
    enabled: !!selectedId,
  });

  if (!selectedId) return (
    <PageWrapper title="Forecasting" subtitle="AI-powered time-series prediction">
      <EmptyState
        icon={LineChart}
        title="No dataset selected"
        description="Select a dataset from the header above to generate a forecast."
        action={
          <Link to="/datasets">
            <Button size="sm" variant="outline">Go to Datasets</Button>
          </Link>
        }
      />
    </PageWrapper>
  );

  if (isLoading) return <PageLoading />;

  // ── Graceful unavailable state ─────────────────────────────────
  // The backend never 422s here anymore -- it always returns
  // {available, unavailable_reason} so we can explain *why* forecasting
  // isn't possible for this specific dataset, with a concrete next step,
  // instead of showing broken/empty charts.
  if (!report?.available) {
    return (
      <PageWrapper title="Forecasting" subtitle="AI-powered time-series prediction">
        <EmptyState
          icon={Clock3}
          tone="warning"
          title="Forecasting isn't available for this dataset"
          description={
            report?.unavailable_reason ??
            "This dataset doesn't have enough structure for a reliable forecast yet."
          }
          action={
            <div className="flex items-center gap-2 mt-1">
              <Link to="/datasets">
                <Button size="sm" variant="outline" className="gap-1.5">
                  <Database className="h-3.5 w-3.5" /> Try another dataset
                </Button>
              </Link>
              <Link to="/eda">
                <Button size="sm" variant="ghost" className="gap-1.5">
                  Review data quality <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
          }
        />
      </PageWrapper>
    );
  }

  const fc = report?.forecast ?? {};
  const overview = report?.overview ?? {};
  const analysis = report?.analysis ?? {};
  const trend = analysis.trend ?? {};
  const seasonality = analysis.seasonality ?? {};
  const hist = fc.historical_dates ?? [];
  const histVals = fc.historical_values ?? [];
  const fcDates = fc.forecast_dates ?? [];
  const fcVals = fc.forecast_values ?? [];
  const isSynthetic = Boolean(overview.synthetic_datetime ?? fc.synthetic_datetime);

  const chartData = [
    ...hist.map((d: string, i: number) => ({ date: d, actual: histVals[i], forecast: null })),
    ...fcDates.map((d: string, i: number) => ({ date: d, actual: null, forecast: fcVals[i] })),
  ];

  const TrendIcon = trend.direction === "increasing" ? TrendingUp : trend.direction === "decreasing" ? TrendingDown : Minus;
  const trendColor = trend.direction === "increasing" ? "text-success" : trend.direction === "decreasing" ? "text-destructive" : "text-muted-foreground";

  return (
    <PageWrapper title="Forecasting" subtitle="AI-powered time-series forecasting">
      {/* Honest disclosure when there's no real date column -- we still
          produce a useful trend forecast using row order, but the user
          should know that's what's happening rather than assume these
          are calendar dates. */}
      {isSynthetic && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-2.5 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3"
        >
          <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            No date column was found in this dataset, so the forecast below uses{" "}
            <span className="text-foreground font-medium">row order</span> as a stand-in
            timeline. The trend is still meaningful; the x-axis just isn't calendar time.
          </p>
        </motion.div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-3">
        <p className="text-xs text-muted-foreground">Forecast periods:</p>
        {[7, 14, 30, 60, 90].map((p) => (
          <Button key={p} size="sm" variant={periods === p ? "default" : "outline"} onClick={() => setPeriods(p)}>
            {p}d
          </Button>
        ))}
      </div>

      {/* Overview */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard title="Model" value={fc.selected_model ?? "—"} color="blue" index={0} />
        <MetricCard title="Target" value={fc.detected_target_column ?? overview.target_column ?? "—"} color="green" index={1} />
        <MetricCard title="RMSE" value={fc.training_metrics?.rmse != null ? Number(fc.training_metrics.rmse).toFixed(2) : "—"} color="amber" index={2} />
        <MetricCard title="MAPE" value={fc.training_metrics?.mape != null ? `${Number(fc.training_metrics.mape).toFixed(1)}%` : "—"} color="red" index={3} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Chart */}
        <Card className="col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Forecast Chart</CardTitle>
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5"><span className="h-2 w-6 bg-primary rounded-full inline-block" />Actual</span>
                <span className="flex items-center gap-1.5"><span className="h-2 w-6 bg-warning rounded-full inline-block" />Forecast</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <EmptyState icon={LineChart} title="No chart data" description="This forecast didn't produce any plottable points." />
            ) : (
              <AreaChart data={chartData.filter((d) => d.actual != null)} xKey="date" yKey="actual" height={240} />
            )}
          </CardContent>
        </Card>

        {/* Analysis */}
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Trend Analysis</CardTitle></CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-3">
                <TrendIcon className={`h-5 w-5 ${trendColor}`} />
                <span className="text-sm font-semibold text-foreground capitalize">{trend.direction ?? "Unknown"}</span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Slope</span>
                  <span className="font-mono text-foreground">{Number(trend.slope ?? 0).toFixed(4)}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Strength</span>
                  <span className="font-mono text-foreground">{Number(trend.strength ?? 0).toFixed(4)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Seasonality</CardTitle></CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-2">
                <Badge variant={seasonality.is_seasonal ? "success" : "outline"}>
                  {seasonality.is_seasonal ? "Detected" : "None"}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">{seasonality.message ?? "No seasonal pattern detected."}</p>
              {seasonality.detected_period && (
                <p className="text-xs text-foreground mt-1">Period: <span className="font-mono">{seasonality.detected_period}</span></p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Confidence</CardTitle></CardHeader>
            <CardContent className="flex justify-center">
              <ScoreGauge
                score={fc.training_metrics?.mape != null ? Math.max(0, Math.round(100 - Number(fc.training_metrics.mape))) : 70}
                label="Forecast Confidence"
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </PageWrapper>
  );
}
