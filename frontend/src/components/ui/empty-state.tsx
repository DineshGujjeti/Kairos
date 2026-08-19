import { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  /** "default" is neutral/informational; "warning" flags a recoverable
   * problem (e.g. forecasting unavailable) without being alarming --
   * every empty state in the app should explain *why* and, where
   * possible, *what to do next*, not just that something is missing. */
  tone?: "default" | "warning";
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  tone = "default",
  className,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn("flex flex-col items-center justify-center py-16 px-4 text-center gap-3", className)}
    >
      <div
        className={cn(
          "h-12 w-12 rounded-2xl flex items-center justify-center",
          tone === "warning" ? "bg-warning/10" : "bg-muted"
        )}
      >
        <Icon className={cn("h-6 w-6", tone === "warning" ? "text-warning" : "text-muted-foreground")} />
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description && (
          <p className="text-xs text-muted-foreground mt-1 max-w-sm leading-relaxed">{description}</p>
        )}
      </div>
      {action}
    </motion.div>
  );
}
