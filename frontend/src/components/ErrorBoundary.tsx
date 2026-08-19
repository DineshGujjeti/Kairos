import { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RotateCw, Home } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Catches render-time errors anywhere below it in the tree and shows a
 * recoverable screen instead of an unrecoverable blank page.
 *
 * Deliberately placed OUTSIDE the Suspense/RequireAuth structure in
 * main.tsx (wrapping <App /> itself), not inside App.tsx's routing --
 * that structure was the exact source of an earlier blank-screen bug
 * (see App.tsx's comments on Suspense placement), and this boundary
 * must not interact with it at all. It only needs to catch genuine
 * unexpected render errors (a malformed API response shaped
 * differently than a page expects, a third-party chart library
 * throwing on edge-case data, etc.) -- routing and auth-redirect logic
 * stays completely untouched.
 *
 * React error boundaries cannot catch errors in event handlers, async
 * code, or the boundary's own render -- this is a safety net for
 * render-time crashes specifically, not a replacement for try/catch
 * around API calls (which is what the toast system + React Query's own
 * isError states handle).
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("Kairos crashed:", error, info.componentStack);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  private handleGoHome = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = "/";
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="w-full max-w-sm text-center space-y-5">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-destructive/10 flex items-center justify-center">
            <AlertTriangle className="h-7 w-7 text-destructive" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Something went wrong</h1>
            <p className="text-sm text-muted-foreground mt-1.5">
              An unexpected error occurred while rendering this page. Your data is safe — this
              is just a display issue.
            </p>
          </div>
          {this.state.error?.message && (
            <p className="text-[11px] font-mono text-muted-foreground bg-muted rounded-lg px-3 py-2 text-left break-words">
              {this.state.error.message}
            </p>
          )}
          <div className="flex items-center justify-center gap-2">
            <button
              onClick={this.handleReset}
              className="inline-flex items-center gap-1.5 h-9 px-4 rounded-lg text-sm font-medium bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
            >
              <RotateCw className="h-3.5 w-3.5" /> Try again
            </button>
            <button
              onClick={this.handleGoHome}
              className="inline-flex items-center gap-1.5 h-9 px-4 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Home className="h-3.5 w-3.5" /> Go to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }
}
