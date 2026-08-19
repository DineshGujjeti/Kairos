import { cn, scoreColor } from "@/lib/utils";

interface ScoreGaugeProps { score: number; label?: string; size?: "sm" | "md" | "lg"; }

export function ScoreGauge({ score, label, size = "md" }: ScoreGaugeProps) {
  const r = size === "lg" ? 44 : size === "md" ? 32 : 22;
  const cx = r + 4; const cy = r + 4;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = score >= 75 ? "#22c55e" : score >= 50 ? "#f59e0b" : "#ef4444";
  const dim = (r + 4) * 2;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={dim} height={dim}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="hsl(217 20% 16%)" strokeWidth={size === "lg" ? 6 : 4} />
        <circle
          cx={cx} cy={cy} r={r} fill="none" stroke={color}
          strokeWidth={size === "lg" ? 6 : 4} strokeDasharray={circ}
          strokeDashoffset={offset} strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cy})`}
          style={{ transition: "stroke-dashoffset 1s ease-out" }}
        />
        <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle"
          fill={color} fontSize={size === "lg" ? 16 : size === "md" ? 13 : 10} fontWeight="600">
          {score}
        </text>
      </svg>
      {label && <p className="text-[10px] text-muted-foreground text-center">{label}</p>}
    </div>
  );
}
