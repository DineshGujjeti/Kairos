import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface AIThinkingProps {
  label?: string;
  className?: string;
}

/**
 * Replaces plain "Loading..." spinners for AI-generated content (Root
 * Cause narratives, Decision recommendations, Executive advisories)
 * with a glowing pulse + label, so waiting for a Gemini call feels
 * like the product is actively reasoning rather than stalled.
 */
export function AIThinking({ label = "AI is analyzing your data…", className }: AIThinkingProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-4 py-16", className)}>
      <div className="relative h-12 w-12">
        <motion.div
          className="absolute inset-0 rounded-full bg-primary/20 blur-lg"
          animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0.9, 0.5] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="relative h-12 w-12 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center"
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
        >
          <Sparkles className="h-5 w-5 text-primary" />
        </motion.div>
      </div>
      <motion.p
        className="text-xs text-muted-foreground"
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      >
        {label}
      </motion.p>
    </div>
  );
}
