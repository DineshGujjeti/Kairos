import { Bell, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDatasetStore } from "@/store/dataset";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const { datasets, selectedId, setSelected } = useDatasetStore();

  const selected = Array.isArray(datasets)
    ? datasets.find((d) => d.id === selectedId)
    : null;

  return (
    <header className="h-14 border-b border-border bg-background/80 backdrop-blur-sm flex items-center justify-between px-6 sticky top-0 z-30">
      <div>
        <h1 className="text-sm font-semibold text-foreground">{title}</h1>
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-2">
        {Array.isArray(datasets) && datasets.length > 0 && (
          <div className="relative">
            <select
              value={selectedId ?? ""}
              onChange={(e) => setSelected(e.target.value || null)}
              className="h-8 pl-3 pr-8 rounded-lg border border-border bg-muted text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring appearance-none cursor-pointer"
            >
              <option value="">Select dataset…</option>

              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>

            <ChevronDown className="absolute right-2 top-2 h-3 w-3 text-muted-foreground pointer-events-none" />
          </div>
        )}

        <Button variant="ghost" size="icon-sm">
          <Bell className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}