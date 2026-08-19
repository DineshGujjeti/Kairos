import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { simulationApi } from "@/lib/api";
import { humanize, cn } from "@/lib/utils";

interface VariableSliderCardProps {
  datasetId: string;
  column: string;
  targetColumn: string;
  mean: number;
  min: number;
  max: number;
  index: number;
}

/**
 * A single "try adjusting this" card: drag the slider, see the
 * predicted effect on the target metric update live. Debounced so
 * dragging doesn't fire a request on every pixel of movement, and made
 * viable by the backend caching the trained model per dataset+target
 * (see model_trainer.train_models_cached) -- without that, every drag
 * tick would retrain a Random Forest from scratch.
 *
 * Deliberately framed in percentage-of-typical terms ("+15% vs
 * typical") rather than asking the user to reason about a raw column
 * value in isolation -- that's the actual UX problem this replaces:
 * picking a column name from a dropdown and typing an arbitrary number
 * with no sense of what's a reasonable value for it.
 */
export function VariableSliderCard({
  datasetId, column, targetColumn, mean, min, max, index,
}: VariableSliderCardProps) {
  // Extend the slider a little past the observed range so "what if we
  // push higher than we've ever gone" is explorable, without allowing
  // wildly unrealistic extrapolation.
  const span = max - min || Math.abs(mean) || 1;
  const sliderMin = min - span * 0.15;
  const sliderMax = max + span * 0.15;

  const [displayValue, setDisplayValue] = useState(mean);
  const [committedValue, setCommittedValue] = useState(mean);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    setDisplayValue(mean);
    setCommittedValue(mean);
  }, [mean, column]);

  const onSlide = (v: number) => {
    setDisplayValue(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setCommittedValue(v), 350);
  };

  const isAtBaseline = Math.abs(committedValue - mean) < span * 0.005;

  const { data: result, isFetching } = useQuery({
    queryKey: ["sim-live", datasetId, column, targetColumn, committedValue.toFixed(4)],
    queryFn: () => simulationApi.single(datasetId, column, committedValue, targetColumn).then((r) => r.data),
    enabled: !isAtBaseline,
    staleTime: 60_000,
  });

  const changeFromTypical = mean !== 0 ? ((displayValue - mean) / Math.abs(mean)) * 100 : 0;
  const deltaPct = result?.delta_pct;
  const direction = deltaPct == null ? null : deltaPct > 1 ? "up" : deltaPct < -1 ? "down" : "flat";
  const DirectionIcon = direction === "up" ? ArrowUpRight : direction === "down" ? ArrowDownRight : Minus;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      className="rounded-xl border border-border bg-card p-4 space-y-3"
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-foreground">{humanize(column)}</p>
        <span className={cn(
          "text-[11px] font-mono px-1.5 py-0.5 rounded-md",
          changeFromTypical > 0.5 ? "text-success bg-success/10" : changeFromTypical < -0.5 ? "text-destructive bg-destructive/10" : "text-muted-foreground bg-muted"
        )}>
          {changeFromTypical >= 0 ? "+" : ""}{changeFromTypical.toFixed(0)}% vs typical
        </span>
      </div>

      <input
        type="range"
        min={sliderMin}
        max={sliderMax}
        step={(sliderMax - sliderMin) / 200}
        value={displayValue}
        onChange={(e) => onSlide(Number(e.target.value))}
        className="w-full accent-primary h-1.5 cursor-pointer"
      />
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>{sliderMin.toFixed(1)}</span>
        <span className="text-foreground font-medium">{displayValue.toFixed(1)}</span>
        <span>{sliderMax.toFixed(1)}</span>
      </div>

      <div className="border-t border-border pt-3 min-h-[3.25rem]">
        {isAtBaseline ? (
          <p className="text-[11px] text-muted-foreground">Drag the slider to see the predicted effect on {humanize(targetColumn)}.</p>
        ) : isFetching && !result ? (
          <p className="text-[11px] text-muted-foreground animate-pulse">Predicting…</p>
        ) : result ? (
          <div className="flex items-center gap-2">
            <DirectionIcon className={cn(
              "h-4 w-4 shrink-0",
              direction === "up" ? "text-success" : direction === "down" ? "text-destructive" : "text-muted-foreground"
            )} />
            <p className="text-xs text-foreground">
              {humanize(targetColumn)} would be{" "}
              <span className="font-semibold tabular-nums">
                <AnimatedNumber value={result.scenario_prediction ?? 0} decimals={1} duration={0.4} />
              </span>
              {" "}
              <span className={cn(
                "font-medium",
                direction === "up" ? "text-success" : direction === "down" ? "text-destructive" : "text-muted-foreground"
              )}>
                ({deltaPct >= 0 ? "+" : ""}{deltaPct?.toFixed(1)}%)
              </span>
            </p>
          </div>
        ) : null}
      </div>
    </motion.div>
  );
}
