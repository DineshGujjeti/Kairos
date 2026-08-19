import { useQuery } from "@tanstack/react-query";
import { Settings, Check, X, Brain, Cpu } from "lucide-react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { aiApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export default function SettingsPage() {
  const { user } = useAuthStore();
  const { data: aiHealth } = useQuery({
    queryKey: ["ai-health"],
    queryFn: () => aiApi.health().then(r => r.data),
  });

  const capabilities = [
    { name: "Secure Authentication" },
    { name: "Dataset Management" },
    { name: "Automated Exploratory Analysis" },
    { name: "KPI Analytics" },
    { name: "Forecasting" },
    { name: "AI Decision Intelligence" },
    { name: "Root Cause Analysis" },
    { name: "What-If Simulation" },
    { name: "Decision Advisor" },
  ];

  return (
    <PageWrapper title="Settings" subtitle="Platform configuration and status">
      <div className="grid grid-cols-2 gap-6">
        {/* Account */}
        <Card>
          <CardHeader><CardTitle>Account</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {[
              { label: "Name", value: user?.full_name ?? "—" },
              { label: "Email", value: user?.email ?? "—" },
              { label: "Role", value: user?.role ?? "—" },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between py-1.5 border-b border-border last:border-0">
                <span className="text-xs text-muted-foreground">{label}</span>
                <span className="text-xs font-medium text-foreground">{value}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* AI Status */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Brain className="h-4 w-4 text-primary" />
              <CardTitle>AI Configuration</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              {aiHealth?.available ? (
                <Check className="h-4 w-4 text-success" />
              ) : (
                <X className="h-4 w-4 text-destructive" />
              )}
              <span className="text-xs text-foreground font-medium">
                Gemini API: {aiHealth?.available ? "Connected" : "Not configured"}
              </span>
              <Badge variant={aiHealth?.available ? "success" : "destructive"}>
                {aiHealth?.available ? "Active" : "Offline"}
              </Badge>
            </div>
            {aiHealth?.model && (
              <div className="flex justify-between py-1.5 border-b border-border">
                <span className="text-xs text-muted-foreground">Model</span>
                <span className="text-xs font-mono text-foreground">{aiHealth.model}</span>
              </div>
            )}
            {!aiHealth?.configured && (
              <div className="rounded-lg bg-muted/50 border border-border p-3">
                <p className="text-xs text-muted-foreground">Set <code className="font-mono text-primary bg-primary/10 px-1 rounded">GEMINI_API_KEY</code> in your <code className="font-mono text-primary bg-primary/10 px-1 rounded">.env</code> file to enable AI features.</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Capabilities */}
        <Card className="col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-primary" />
              <CardTitle>What Kairos Can Do</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-2">
              {capabilities.map((m) => (
                <div key={m.name} className="flex items-center gap-2 p-2.5 rounded-lg bg-muted/50">
                  <Check className="h-3.5 w-3.5 text-success shrink-0" />
                  <span className="text-xs text-foreground">{m.name}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}
