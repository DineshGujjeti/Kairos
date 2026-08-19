import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { AssistantWidget } from "@/components/assistant/AssistantWidget";

export function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex-1 ml-56 flex flex-col overflow-hidden">
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
      <AssistantWidget />
    </div>
  );
}
