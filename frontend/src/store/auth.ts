import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  org_id?: string;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  setUser: (user: AuthUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      // Derived on rehydration in onRehydrateStorage — kept false as initial
      isAuthenticated: false,
      setToken: (token) => {
        localStorage.setItem("kairos_token", token);
        set({ token, isAuthenticated: true });
      },
      setUser: (user) => set({ user }),
      logout: () => {
        localStorage.removeItem("kairos_token");
        set({ token: null, user: null, isAuthenticated: false });
      },
    }),
    {
      name: "kairos-auth",
      // Persist all three fields
      partialize: (s) => ({ token: s.token, user: s.user, isAuthenticated: !!s.token }),
      // After rehydration, re-derive isAuthenticated from token so a stale
      // isAuthenticated=false in storage never blocks an authenticated user.
      onRehydrateStorage: () => (state) => {
        if (state && state.token) {
          state.isAuthenticated = true;
        }
      },
    }
  )
);
