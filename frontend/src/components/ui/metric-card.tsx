import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";
import { MiniSparkline } from "@/components/charts/MiniSparkline";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon?: LucideIcon;
  sparkline?: number[];
  color?: "blue" | "green" | "amber" | "red";
  subtitle?: string;
  index?: number;
}

const colorMap = {
  blue: { icon: "text-primary bg-primary/10", change: "text-primary" },
  green: { icon: "text-success bg-success/10", change: "text-success" },
  amber: { icon: "text-warning bg-warning/10", change: "text-warning" },
  red: { icon: "text-destructive bg-destructive/10", change: "text-destructive" },
};

export function MetricCard({ title, value, change, icon: Icon, sparkline, color = "blue", subtitle, index = 0 }: MetricCardProps) {
  const colors = colorMap[color];
  const isPositive = (change ?? 0) >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      className="rounded-xl border border-border bg-card p-4 flex flex-col gap-3"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-muted-foreground truncate">{title}</p>
          <p className="text-xl font-semibold text-foreground mt-0.5 tabular-nums">{value}</p>
          {subtitle && <p className="text-[10px] text-muted-foreground mt-0.5 truncate">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center shrink-0", colors.icon)}>
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      {(change !== undefined || sparkline) && (
        <div className="flex items-end justify-between gap-2">
          {change !== undefined && (
            <span className={cn("text-xs font-medium", isPositive ? "text-success" : "text-destructive")}>
              {isPositive ? "+" : ""}{change.toFixed(1)}%
              <span className="text-muted-foreground font-normal ml-1">vs avg</span>
            </span>
          )}
          {sparkline && (
            <div className="flex-1">
              <MiniSparkline data={sparkline} color={color === "green" ? "#22c55e" : color === "amber" ? "#f59e0b" : color === "red" ? "#ef4444" : "#3b82f6"} />
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
