import { motion } from "framer-motion";
import {
  Sparkles, Calendar, Hash, Tag, CheckCircle2, ArrowRight, Fingerprint,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { cn } from "@/lib/utils";

interface ColumnProfileShape {
  row_count: number;
  column_count: number;
  domain_guess: string;
  domain_confidence: number;
  roles: Record<string, string[]>;
  best_datetime_column: string | null;
  target_candidates: string[];
  primary_dimensions: string[];
  primary_measures: string[];
}

interface DatasetProfileRevealProps {
  profile: ColumnProfileShape;
  fileName: string;
  onContinue: () => void;
}

const ROLE_META: Record<string, { label: string; icon: typeof Hash; color: string }> = {
  numeric_measure: { label: "Measures", icon: Hash, color: "text-primary" },
  categorical_dimension: { label: "Dimensions", icon: Tag, color: "text-warning" },
  datetime: { label: "Date/Time", icon: Calendar, color: "text-success" },
  id: { label: "Identifiers", icon: Fingerprint, color: "text-muted-foreground" },
};

/**
 * The "AI analyzed your dataset" reveal shown right after upload --
 * this is the direct replacement for the old Dataset Type dropdown.
 * Instead of asking the user what kind of data it is, it tells them
 * what was detected and lets them confirm and move on, the same way a
 * modern AI product (not an admin form) would.
 */
export function DatasetProfileReveal({ profile, fileName, onContinue }: DatasetProfileRevealProps) {
  const confidencePct = Math.round((profile.domain_confidence ?? 0) * 100);
  const isConfident = confidencePct >= 40;

  const roleGroups = (["numeric_measure", "categorical_dimension", "datetime", "id"] as const)
    .map((role) => ({ role, meta: ROLE_META[role], columns: profile.roles?.[role] ?? [] }))
    .filter((g) => g.columns.length > 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="rounded-2xl border border-primary/20 bg-gradient-to-b from-primary/[0.06] to-transparent p-6 space-y-5"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <motion.div
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
          className="h-9 w-9 rounded-xl bg-primary/15 flex items-center justify-center shrink-0"
        >
          <Sparkles className="h-4 w-4 text-primary" />
        </motion.div>
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">AI analyzed <span className="text-foreground font-medium">{fileName}</span></p>
          <div className="flex items-center gap-2">
            <p className="text-base font-semibold text-foreground">
              {isConfident ? profile.domain_guess : "General Business Dataset"}
            </p>
            {isConfident && (
              <span className="text-xs font-medium text-primary tabular-nums">
                <AnimatedNumber value={confidencePct} suffix="%" duration={0.9} />
              </span>
            )}
          </div>
        </div>
      </div>

      {!isConfident && (
        <p className="text-xs text-muted-foreground -mt-2">
          We couldn't confidently match this to a specific business domain, so general-purpose
          analytics will be used. Everything below still works.
        </p>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-border bg-card/60 p-3 text-center">
          <p className="text-lg font-semibold text-foreground tabular-nums">
            <AnimatedNumber value={profile.row_count} />
          </p>
          <p className="text-[10px] text-muted-foreground mt-0.5">Rows</p>
        </div>
        <div className="rounded-xl border border-border bg-card/60 p-3 text-center">
          <p className="text-lg font-semibold text-foreground tabular-nums">
            <AnimatedNumber value={profile.column_count} />
          </p>
          <p className="text-[10px] text-muted-foreground mt-0.5">Columns</p>
        </div>
        <div className="rounded-xl border border-border bg-card/60 p-3 text-center">
          <p className="text-lg font-semibold text-foreground truncate px-1">
            {profile.best_datetime_column ?? "None found"}
          </p>
          <p className="text-[10px] text-muted-foreground mt-0.5">Time column</p>
        </div>
      </div>

      {/* Detected roles */}
      <div className="space-y-3">
        {roleGroups.map((group, i) => {
          const Icon = group.meta.icon;
          return (
            <motion.div
              key={group.role}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 + i * 0.06 }}
              className="flex items-start gap-3"
            >
              <div className={cn("flex items-center gap-1.5 w-28 shrink-0 pt-0.5", group.meta.color)}>
                <Icon className="h-3.5 w-3.5" />
                <span className="text-xs font-medium">{group.meta.label}</span>
              </div>
              <div className="flex flex-wrap gap-1.5 flex-1">
                {group.columns.slice(0, 8).map((col) => (
                  <span
                    key={col}
                    className={cn(
                      "text-[11px] px-2 py-0.5 rounded-md border bg-muted/60 text-foreground/90 border-border",
                      profile.target_candidates?.[0] === col && "border-primary/40 bg-primary/10 text-primary"
                    )}
                  >
                    {col}
                  </span>
                ))}
                {group.columns.length > 8 && (
                  <span className="text-[11px] text-muted-foreground px-1 py-0.5">
                    +{group.columns.length - 8} more
                  </span>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>

      {profile.target_candidates?.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="flex items-center gap-2 text-xs text-muted-foreground border-t border-border pt-3"
        >
          <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0" />
          <span>
            We'll suggest <span className="text-foreground font-medium">{profile.target_candidates[0]}</span> as
            the primary metric to analyze -- you can change this anytime.
          </span>
        </motion.div>
      )}

      <div className="flex justify-end pt-1">
        <Button onClick={onContinue} className="gap-1.5">
          Continue <ArrowRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </motion.div>
  );
}
