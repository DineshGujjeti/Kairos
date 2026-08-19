import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmt(value: number, opts?: Intl.NumberFormatOptions) {
  return new Intl.NumberFormat("en-US", opts).format(value);
}

export function fmtPct(value: number, decimals = 1) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(decimals)}%`;
}

export function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function truncate(str: string, n = 40) {
  return str.length > n ? str.slice(0, n) + "…" : str;
}

export function scoreColor(score: number) {
  if (score >= 75) return "text-success";
  if (score >= 50) return "text-warning";
  return "text-destructive";
}

export function priorityColor(priority: string) {
  switch (priority.toLowerCase()) {
    case "high": return "text-destructive bg-destructive/10 border-destructive/20";
    case "medium": return "text-warning bg-warning/10 border-warning/20";
    default: return "text-muted-foreground bg-muted border-border";
  }
}

/** order_total -> Order Total, avgResponseTime -> Avg Response Time.
 * Mirrors the backend's smart_cards._humanize so column names read the
 * same way everywhere a raw column name would otherwise leak into the UI. */
export function humanize(name: string): string {
  const spaced = name.replace(/(?<!^)(?=[A-Z])/g, " ").replace(/[_-]/g, " ");
  return spaced
    .split(" ")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ") || name;
}
