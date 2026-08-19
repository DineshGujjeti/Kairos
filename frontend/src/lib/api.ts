import axios from "axios";

const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("kairos_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    // Only force-logout on 401 for non-auth endpoints to avoid redirect loops
    if (
      err.response?.status === 401 &&
      !err.config?.url?.includes("/auth/login") &&
      !err.config?.url?.includes("/auth/register")
    ) {
      localStorage.removeItem("kairos_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;

// ── Auth ──────────────────────────────────────────────────────────
export const authApi = {
  /**
   * Backend OAuth2PasswordRequestForm requires:
   *   Content-Type: application/x-www-form-urlencoded
   *   Fields: username (maps to email), password
   */
  login: (email: string, password: string) => {
    const body = new URLSearchParams();
    body.append("username", email);
    body.append("password", password);
    return api.post("/auth/login", body, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    organization_name: string;
  }) => api.post("/auth/register", data),

  me: () => api.get("/auth/me"),
};

// ── Datasets ──────────────────────────────────────────────────────
export const datasetsApi = {
  list: () => api.get("/datasets"),
  get: (id: string) => api.get(`/datasets/${id}`),
  preview: (id: string) => api.get(`/datasets/${id}/preview`),
  /**
   * No dataset_type parameter -- the backend defaults every upload to
   * dataset_type=general and profiles it automatically via
   * dataset_intelligence.py. Asking the user to pre-classify their data
   * (Orders? HR? Retail?) before an AI platform has even looked at it
   * defeats the point of automatic detection, so the frontend never
   * sends this field at all.
   */
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post("/datasets/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  delete: (id: string) => api.delete(`/datasets/${id}`),
};

// ── EDA ───────────────────────────────────────────────────────────
export const edaApi = {
  summary: (id: string) => api.get(`/eda/${id}/summary`),
  statistics: (id: string) => api.get(`/eda/${id}/statistics`),
  quality: (id: string) => api.get(`/eda/${id}/quality`),
  correlation: (id: string) => api.get(`/eda/${id}/correlation`),
  outliers: (id: string) => api.get(`/eda/${id}/outliers`),
  distribution: (id: string) => api.get(`/eda/${id}/distribution`),
  insights: (id: string) => api.get(`/eda/${id}/insights`),
  report: (id: string) => api.get(`/eda/${id}/report`),
};

// ── KPI ───────────────────────────────────────────────────────────
export const kpiApi = {
  overview: (id: string) => api.get(`/kpi/${id}/overview`),
  metrics: (id: string) => api.get(`/kpi/${id}/metrics`),
  dashboard: (id: string) => api.get(`/kpi/${id}/dashboard`),
  alerts: (id: string) => api.get(`/kpi/${id}/alerts`),
  trend: (id: string, metric: string) =>
    api.get(`/kpi/${id}/trend?metric=${metric}`),
  // Curated, business-readable KPI cards -- the headline metrics with
  // plain-language descriptions and trends, distinct from the raw
  // per-column statistics returned by metrics().
  smartCards: (id: string, maxCards = 6) =>
    api.get(`/kpi/${id}/smart-cards?max_cards=${maxCards}`),
};

// ── Forecasting ───────────────────────────────────────────────────
export const forecastApi = {
  overview: (id: string) => api.get(`/forecasting/${id}/overview`),
  forecast: (id: string, periods = 30) =>
    api.post(`/forecasting/${id}/forecast`, { periods }),
  analysis: (id: string) => api.get(`/forecasting/${id}/analysis`),
  report: (id: string, periods = 30) =>
    api.post(`/forecasting/${id}/report`, { periods }),
};

// ── Root Cause ────────────────────────────────────────────────────
export const rootCauseApi = {
  analyze: (id: string, target?: string) =>
    api.post(`/ai/${id}/root-cause`, { target_column: target ?? null }),
  drivers: (id: string, target?: string) =>
    api.get(
      `/ai/${id}/drivers${target ? `?target_column=${encodeURIComponent(target)}` : ""}`
    ),
  contributions: (id: string, target?: string) =>
    api.get(
      `/ai/${id}/contributions${target ? `?target_column=${encodeURIComponent(target)}` : ""}`
    ),
};

// ── Simulation ────────────────────────────────────────────────────
export const simulationApi = {
  train: (id: string, target?: string) =>
    api.post(`/simulation/${id}/train`, { target_column: target ?? null }),
  single: (
    id: string,
    variable: string,
    new_value: number,
    target?: string
  ) =>
    api.post(`/simulation/${id}/single`, {
      variable,
      new_value,
      target_column: target ?? null,
    }),
  multi: (
    id: string,
    scenario: Record<string, number>,
    target?: string
  ) =>
    api.post(`/simulation/${id}/multi`, {
      scenario,
      target_column: target ?? null,
    }),
  sensitivity: (id: string, target?: string) =>
    api.post(`/simulation/${id}/sensitivity`, {
      target_column: target ?? null,
    }),
  compare: (
    id: string,
    scenarios: Array<{ name: string; variables: Record<string, number> }>,
    target?: string
  ) =>
    api.post(`/simulation/${id}/compare`, {
      scenarios,
      target_column: target ?? null,
    }),
};

// ── Decision ──────────────────────────────────────────────────────
export const decisionApi = {
  analyze: (dataset_id: string) =>
    api.post("/decision/analyze", { dataset_id }),
  recommend: (dataset_id: string, metric_focus?: string) =>
    api.post("/decision/recommend", { dataset_id, metric_focus }),
  executive: (dataset_id: string) =>
    api.post("/decision/executive", { dataset_id }),
  prescriptive: (dataset_id: string, metric_focus?: string) =>
    api.post("/decision/prescriptive", { dataset_id, metric_focus }),
  rootCause: (dataset_id: string, problem: string) =>
    api.post("/decision/root-cause", {
      dataset_id,
      problem_statement: problem,
    }),
  history: () => api.get("/decision/history"),
};

// ── AI ─────────────────────────────────────────────────────────────
export const aiApi = {
  health: () => api.get("/ai/health"),
  summary: (id: string) => api.get(`/ai/${id}/summary`),
  question: (id: string, question: string) =>
    api.post(`/ai/${id}/question`, { question }),
  insights: (id: string) =>
    api.post(`/ai/${id}/analyze`, { template_name: "business_insights" }),
  risks: (id: string) => api.get(`/ai/${id}/risks`),
  opportunities: (id: string) => api.get(`/ai/${id}/opportunities`),
  recommendations: (id: string) => api.get(`/ai/${id}/recommendations`),
  // In-app help assistant -- conversational, works with or without a
  // dataset selected and with or without Gemini configured.
  chat: (
    message: string,
    opts?: { datasetId?: string; currentPage?: string; history?: Array<{ role: "user" | "assistant"; content: string }> }
  ) =>
    api.post("/ai/assistant/chat", {
      message,
      dataset_id: opts?.datasetId,
      current_page: opts?.currentPage,
      history: opts?.history ?? [],
    }),
};
