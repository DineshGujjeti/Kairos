import { BarChart as RechartsBar, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface BarChartProps {
  data: Array<Record<string, unknown>>;
  xKey: string;
  yKey: string;
  color?: string;
  height?: number;
  colorFn?: (v: number) => string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-card p-2.5 shadow-lg">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-sm font-semibold text-foreground">{Number(payload[0].value).toLocaleString()}</p>
    </div>
  );
};

export function BarChart({ data, xKey, yKey, color = "#3b82f6", height = 220, colorFn }: BarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBar data={data} barSize={20}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 20% 16%)" vertical={false} />
        <XAxis dataKey={xKey} tick={{ fill: "hsl(215 16% 50%)", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: "hsl(215 16% 50%)", fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey={yKey} fill={color} radius={[4, 4, 0, 0]}>
          {colorFn && data.map((entry, i) => (
            <Cell key={i} fill={colorFn(Number(entry[yKey]))} />
          ))}
        </Bar>
      </RechartsBar>
    </ResponsiveContainer>
  );
}
