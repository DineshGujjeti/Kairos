import { cn } from "@/lib/utils";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";

type AlertVariant = "default" | "success" | "warning" | "destructive";

const variantStyles: Record<AlertVariant, { wrap: string; icon: React.ElementType; iconClass: string }> = {
  default: { wrap: "border-border bg-muted/50", icon: Info, iconClass: "text-muted-foreground" },
  success: { wrap: "border-success/20 bg-success/5", icon: CheckCircle2, iconClass: "text-success" },
  warning: { wrap: "border-warning/20 bg-warning/5", icon: AlertTriangle, iconClass: "text-warning" },
  destructive: { wrap: "border-destructive/20 bg-destructive/5", icon: XCircle, iconClass: "text-destructive" },
};

interface AlertProps { variant?: AlertVariant; title?: string; children: React.ReactNode; className?: string; }

export function Alert({ variant = "default", title, children, className }: AlertProps) {
  const { wrap, icon: Icon, iconClass } = variantStyles[variant];
  return (
    <div className={cn("flex gap-3 rounded-xl border p-4", wrap, className)}>
      <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", iconClass)} />
      <div className="flex-1 min-w-0">
        {title && <p className="text-sm font-medium text-foreground mb-0.5">{title}</p>}
        <div className="text-xs text-muted-foreground leading-relaxed">{children}</div>
      </div>
    </div>
  );
}
