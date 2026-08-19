import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { Loader2, Zap, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

const schema = z.object({
  full_name: z.string().min(2, "Name must be at least 2 characters"),
  organization_name: z.string().min(2, "Organisation must be at least 2 characters"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});
type Form = z.infer<typeof schema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const { setToken, setUser } = useAuthStore();
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Form>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: Form) => {
    setError("");
    setSuccess(false);

    // Step 1: Register
    try {
      await authApi.register(data);
    } catch (err: any) {
      // Extract a readable error string regardless of whether detail is a
      // string, array of validation objects, or something else entirely.
      const detail = err?.response?.data?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else if (Array.isArray(detail)) {
        // FastAPI validation errors: [{msg, loc, ...}]
        setError(detail.map((d: any) => d.msg ?? String(d)).join(". "));
      } else {
        setError("Registration failed. Please try again.");
      }
      return; // Stop — do not attempt login
    }

    // Step 2: Auto-login with form-urlencoded (same fix as LoginPage)
    try {
      const res = await authApi.login(data.email, data.password);
      const token: string = res.data.access_token;
      if (!token) throw new Error("No token returned after registration");

      setToken(token);
      const me = await authApi.me();
      setUser(me.data);

      setSuccess(true);
      // Brief delay so user sees the success state, then navigate
      setTimeout(() => navigate("/", { replace: true }), 600);
    } catch (err: any) {
      // Registration succeeded but auto-login failed — send to login page
      // so the user can sign in manually. Never leave a blank screen.
      setError(
        "Account created! Please sign in to continue."
      );
      setTimeout(() => navigate("/login", { replace: true }), 1500);
    }
  };

  const fields: Array<{
    id: keyof Form;
    label: string;
    placeholder: string;
    type: string;
    autoComplete: string;
  }> = [
    { id: "full_name", label: "Full Name", placeholder: "Jane Smith", type: "text", autoComplete: "name" },
    { id: "organization_name", label: "Organisation", placeholder: "Acme Corp", type: "text", autoComplete: "organization" },
    { id: "email", label: "Email", placeholder: "jane@acme.com", type: "email", autoComplete: "email" },
    { id: "password", label: "Password", placeholder: "Min 8 characters", type: "password", autoComplete: "new-password" },
  ];

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-primary/5 blur-[120px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="w-full max-w-sm relative"
      >
        <div className="text-center mb-8">
          <div className="inline-flex h-12 w-12 rounded-2xl bg-primary items-center justify-center mb-4 shadow-lg shadow-primary/30">
            <Zap className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">
            Get started
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create your Kairos workspace
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-6 shadow-2xl shadow-black/40">
          {success ? (
            <div className="flex flex-col items-center gap-3 py-6 text-center">
              <CheckCircle2 className="h-10 w-10 text-success" />
              <p className="text-sm font-semibold text-foreground">Account created!</p>
              <p className="text-xs text-muted-foreground">Redirecting to dashboard…</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {fields.map(({ id, label, placeholder, type, autoComplete }) => (
                <div key={id} className="space-y-1.5">
                  <Label htmlFor={id}>{label}</Label>
                  <Input
                    id={id}
                    type={type}
                    placeholder={placeholder}
                    autoComplete={autoComplete}
                    {...register(id)}
                  />
                  {errors[id] && (
                    <p className="text-xs text-destructive">{errors[id]?.message}</p>
                  )}
                </div>
              ))}

              {error && (
                <p
                  className={`text-xs rounded-lg px-3 py-2 border ${
                    error.startsWith("Account created")
                      ? "text-success bg-success/10 border-success/20"
                      : "text-destructive bg-destructive/10 border-destructive/20"
                  }`}
                >
                  {error}
                </p>
              )}

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating account…
                  </>
                ) : (
                  "Create account"
                )}
              </Button>
            </form>
          )}

          <p className="text-xs text-muted-foreground text-center mt-4">
            Already have an account?{" "}
            <Link to="/login" className="text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
