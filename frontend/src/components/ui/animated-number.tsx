import { useEffect, useRef, useState } from "react";
import { animate, useMotionValue } from "framer-motion";

interface AnimatedNumberProps {
  value: number;
  duration?: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
  className?: string;
}

/**
 * Counts up (or down) to `value` whenever it changes, instead of
 * snapping instantly. Used anywhere a number is the payoff of an
 * analysis -- confidence scores, KPI values, detected row counts --
 * so the UI feels like it's "revealing" a result rather than just
 * rendering static data.
 */
export function AnimatedNumber({
  value,
  duration = 0.8,
  decimals = 0,
  suffix = "",
  prefix = "",
  className,
}: AnimatedNumberProps) {
  const motionValue = useMotionValue(0);
  const [display, setDisplay] = useState("0");
  const isFirstRender = useRef(true);

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration: isFirstRender.current ? duration : Math.min(duration, 0.5),
      ease: "easeOut",
      onUpdate: (latest) => {
        setDisplay(
          decimals > 0 ? latest.toFixed(decimals) : Math.round(latest).toLocaleString()
        );
      },
    });
    isFirstRender.current = false;
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <span className={className}>
      {prefix}
      {display}
      {suffix}
    </span>
  );
}
