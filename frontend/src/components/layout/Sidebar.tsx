import { NavLink, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard, Database, BarChart3, TrendingUp, LineChart,
  Brain, Zap, Lightbulb, History, Settings, LogOut, Cpu,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

const nav = [
  { label: "Overview", href: "/", icon: LayoutDashboard },
  { label: "Datasets", href: "/datasets", icon: Database },
  { type: "separator", label: "Analytics" },
  { label: "EDA", href: "/eda", icon: BarChart3 },
  { label: "KPI Analytics", href: "/kpi", icon: TrendingUp },
  { label: "Forecasting", href: "/forecasting", icon: LineChart },
  { type: "separator", label: "Intelligence" },
  { label: "Root Cause", href: "/root-cause", icon: Brain },
  { label: "What-If Simulation", href: "/simulation", icon: Zap },
  { label: "Decision Advisor", href: "/decision", icon: Lightbulb },
  { label: "Executive Advisor", href: "/executive", icon: Cpu },
  { type: "separator", label: "System" },
  { label: "History", href: "/history", icon: History },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate("/login"); };

  return (
    <motion.aside
      initial={{ x: -240 }}
      animate={{ x: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="fixed left-0 top-0 h-screen w-56 bg-sidebar border-r border-border flex flex-col z-40"
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-border">
        <div className="h-7 w-7 rounded-lg bg-primary flex items-center justify-center">
          <span className="text-primary-foreground font-bold text-xs">K</span>
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground tracking-tight">Kairos</p>
          <p className="text-[10px] text-muted-foreground">Decision Intelligence</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto scrollbar-none px-3 py-3 space-y-0.5">
        {nav.map((item, i) => {
          if (item.type === "separator") {
            return (
              <div key={i} className="pt-4 pb-1.5 px-2">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">{item.label}</p>
              </div>
            );
          }
          const Icon = item.icon!;
          return (
            <NavLink key={item.href} to={item.href!} end={item.href === "/"}>
              {({ isActive }) => (
                <span className={cn(
                  "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition-all group",
                  isActive
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )}>
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="flex-1 truncate">{item.label}</span>
                  {isActive && <ChevronRight className="h-3 w-3 opacity-60" />}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* User */}
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-2.5 px-2 py-2 rounded-lg hover:bg-accent group cursor-pointer" onClick={handleLogout}>
          <div className="h-7 w-7 rounded-full bg-secondary flex items-center justify-center text-xs font-semibold text-muted-foreground">
            {user?.full_name?.[0]?.toUpperCase() ?? "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-foreground truncate">{user?.full_name ?? "User"}</p>
            <p className="text-[10px] text-muted-foreground truncate">{user?.email ?? ""}</p>
          </div>
          <LogOut className="h-3.5 w-3.5 text-muted-foreground group-hover:text-destructive transition-colors" />
        </div>
      </div>
    </motion.aside>
  );
}
