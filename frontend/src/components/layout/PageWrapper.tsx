import { motion } from "framer-motion";
import { Header } from "./Header";

interface PageWrapperProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}

export function PageWrapper({ title, subtitle, children, actions }: PageWrapperProps) {
  return (
    <div className="flex flex-col min-h-full">
      <Header title={title} subtitle={subtitle} />
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="flex-1 p-6 space-y-6"
      >
        {actions && <div className="flex items-center justify-between">{actions}</div>}
        {children}
      </motion.div>
    </div>
  );
}
