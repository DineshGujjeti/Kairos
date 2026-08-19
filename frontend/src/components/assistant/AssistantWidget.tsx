import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { MessageCircle, X, Send, Sparkles } from "lucide-react";
import { aiApi } from "@/lib/api";
import { useDatasetStore } from "@/store/dataset";
import { cn } from "@/lib/utils";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const PAGE_LABELS: Record<string, string> = {
  "/": "Dashboard",
  "/datasets": "Datasets",
  "/eda": "EDA",
  "/kpi": "KPI Analytics",
  "/forecasting": "Forecasting",
  "/root-cause": "Root Cause Analysis",
  "/simulation": "What-If Simulation",
  "/decision": "Decision Advisor",
  "/executive": "Executive Advisor",
  "/history": "History",
  "/settings": "Settings",
};

const SUGGESTED_QUESTIONS = [
  "How does forecasting work without a date column?",
  "What does the confidence score mean?",
  "How do I run a what-if simulation?",
  "What can Decision Advisor do?",
];

/**
 * A persistent, floating help assistant mounted once in AppLayout so
 * it's available on every protected page. Deliberately NOT mounted on
 * /login or /register -- there's nothing to help with before someone
 * is signed in and looking at actual data.
 *
 * Sends the current page and (if one is selected) the active dataset
 * as context with every message, so answers can be specific rather
 * than generic -- this mirrors what the backend assistant module
 * expects (see app.services.ai.assistant.answer_assistant_query).
 */
export function AssistantWidget() {
  const location = useLocation();
  const { selectedId } = useDatasetStore();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  const currentPage = PAGE_LABELS[location.pathname] ?? undefined;

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isSending) return;

    const userMessage: ChatMessage = { role: "user", content: trimmed };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput("");
    setIsSending(true);

    try {
      const res = await aiApi.chat(trimmed, {
        datasetId: selectedId ?? undefined,
        currentPage,
        history: nextMessages.slice(-6),
      });
      setMessages((prev) => [...prev, { role: "assistant", content: res.data.reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I couldn't reach the assistant just now. Please try again." },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <>
      {/* Floating trigger */}
      <AnimatePresence>
        {!open && (
          <motion.button
            key="trigger"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={() => setOpen(true)}
            className="fixed bottom-5 right-5 z-40 h-12 w-12 rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/30 flex items-center justify-center"
            title="Ask Kairos Assistant"
          >
            <motion.div
              className="absolute inset-0 rounded-full bg-primary/40"
              animate={{ scale: [1, 1.4, 1], opacity: [0.6, 0, 0.6] }}
              transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
            />
            <MessageCircle className="h-5 w-5 relative" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
            className="fixed bottom-5 right-5 z-40 w-[360px] h-[520px] rounded-2xl border border-border bg-card shadow-2xl shadow-black/50 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center gap-2.5 px-4 py-3 border-b border-border bg-gradient-to-r from-primary/10 to-transparent">
              <div className="h-7 w-7 rounded-lg bg-primary/15 flex items-center justify-center shrink-0">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-foreground">Kairos Assistant</p>
                <p className="text-[10px] text-muted-foreground truncate">
                  {currentPage ? `Helping with ${currentPage}` : "Ask me anything about Kairos"}
                </p>
              </div>
              <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 scrollbar-none">
              {messages.length === 0 ? (
                <div className="space-y-3 pt-2">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Hi! I can help you understand what a page does, interpret a result, or find
                    your way around Kairos. Try one of these, or just type your own question:
                  </p>
                  <div className="flex flex-col gap-1.5">
                    {SUGGESTED_QUESTIONS.map((q) => (
                      <button
                        key={q}
                        onClick={() => send(q)}
                        className="text-left text-[11px] rounded-lg border border-border px-3 py-2 text-muted-foreground hover:text-foreground hover:border-primary/30 hover:bg-accent transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((m, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
                  >
                    <div
                      className={cn(
                        "max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed",
                        m.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-foreground border border-border"
                      )}
                    >
                      {m.content}
                    </div>
                  </motion.div>
                ))
              )}
              {isSending && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                  <div className="bg-muted border border-border rounded-xl px-3 py-2.5 flex items-center gap-1">
                    {[0, 1, 2].map((i) => (
                      <motion.span
                        key={i}
                        className="h-1.5 w-1.5 rounded-full bg-muted-foreground"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.15 }}
                      />
                    ))}
                  </div>
                </motion.div>
              )}
            </div>

            {/* Input */}
            <form
              onSubmit={(e) => { e.preventDefault(); send(input); }}
              className="flex items-center gap-2 px-3 py-3 border-t border-border"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question…"
                className="flex-1 h-9 rounded-lg border border-input bg-muted px-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
              <button
                type="submit"
                disabled={!input.trim() || isSending}
                className="h-9 w-9 rounded-lg bg-primary text-primary-foreground flex items-center justify-center disabled:opacity-40 transition-opacity shrink-0"
              >
                <Send className="h-3.5 w-3.5" />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
