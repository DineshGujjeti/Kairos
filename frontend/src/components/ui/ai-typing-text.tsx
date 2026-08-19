import { useEffect, useState } from "react";
import { motion } from "framer-motion";

interface AITypingTextProps {
  text: string;
  speed?: number; // ms per word
  className?: string;
  onComplete?: () => void;
}

/**
 * Reveals `text` progressively, word by word (character-level typing
 * reads as slow/gimmicky for paragraph-length AI output; word-level
 * reads as "generating" without making the user wait). Resets cleanly
 * whenever `text` changes so switching datasets never leaves a
 * half-typed sentence on screen.
 */
export function AITypingText({ text, speed = 18, className, onComplete }: AITypingTextProps) {
  const [wordCount, setWordCount] = useState(0);
  const words = text ? text.split(" ") : [];

  useEffect(() => {
    setWordCount(0);
    if (!text) return;

    let cancelled = false;
    let i = 0;
    const step = () => {
      if (cancelled) return;
      i += 1;
      setWordCount(i);
      if (i < words.length) {
        setTimeout(step, speed);
      } else {
        onComplete?.();
      }
    };
    const timer = setTimeout(step, speed);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);

  const revealed = words.slice(0, wordCount).join(" ");
  const isComplete = wordCount >= words.length;

  return (
    <span className={className}>
      {revealed}
      {!isComplete && text && (
        <motion.span
          className="inline-block w-1.5 h-3.5 ml-0.5 bg-primary align-middle"
          animate={{ opacity: [1, 0, 1] }}
          transition={{ duration: 0.8, repeat: Infinity, ease: "easeInOut" }}
        />
      )}
    </span>
  );
}
