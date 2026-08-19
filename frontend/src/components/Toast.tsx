import { createContext, useCallback, useContext, useState, ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, XCircle, Info, AlertTriangle, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastVariant = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  toast: (t: Omit<Toast, "id">) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const VARIANT_META: Record<ToastVariant, { icon: typeof CheckCircle2; className: string }> = {
  success: { icon: CheckCircle2, className: "border-success/30 bg-success/10 text-success" },
  error: { icon: XCircle, className: "border-destructive/30 bg-destructive/10 text-destructive" },
  info: { icon: Info, className: "border-primary/30 bg-primary/10 text-primary" },
  warning: { icon: AlertTriangle, className: "border-warning/30 bg-warning/10 text-warning" },
};

/**
 * A dependency-free toast/notification system (no new packages -- just
 * React context + the framer-motion the app already uses). Exists to
 * replace the two reliability gaps this app previously had:
 *   1. Destructive actions (deleting a dataset) used the browser's
 *      native confirm() -- jarring and inconsistent with the rest of
 *      the UI. That's replaced with a proper in-app confirmation.
 *   2. Background actions that failed (upload errors, delete failures)
 *      had no consistent user-facing feedback beyond an inline message
 *      that only appeared if the user was looking at the right spot.
 *      toast() gives every async action a guaranteed, visible outcome.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((t: Omit<Toast, "id">) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { ...t, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, 5000);
  }, []);

  const dismiss = (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-full max-w-sm pointer-events-none">
        <AnimatePresence>
          {toasts.map((t) => {
            const meta = VARIANT_META[t.variant];
            const Icon = meta.icon;
            return (
              <motion.div
                key={t.id}
                initial={{ opacity: 0, y: 12, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 40, transition: { duration: 0.2 } }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
                className={cn(
                  "pointer-events-auto flex items-start gap-2.5 rounded-xl border px-4 py-3 shadow-2xl shadow-black/40 backdrop-blur-sm bg-card",
                  meta.className
                )}
              >
                <Icon className="h-4 w-4 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-foreground">{t.title}</p>
                  {t.description && <p className="text-[11px] text-muted-foreground mt-0.5">{t.description}</p>}
                </div>
                <button onClick={() => dismiss(t.id)} className="shrink-0 text-muted-foreground hover:text-foreground transition-colors">
                  <X className="h-3.5 w-3.5" />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within a ToastProvider");
  return ctx.toast;
}
