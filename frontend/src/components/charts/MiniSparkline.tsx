import { LineChart, Line, ResponsiveContainer } from "recharts";

interface MiniSparklineProps { data: number[]; color?: string; }

export function MiniSparkline({ data, color = "#3b82f6" }: MiniSparklineProps) {
  const chartData = data.map((v) => ({ v }));
  return (
    <ResponsiveContainer width="100%" height={36}>
      <LineChart data={chartData}>
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
