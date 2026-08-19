import { create } from "zustand";

interface Dataset { id: string; name: string; dataset_type: string; status: string; created_at: string; row_count?: number; column_count?: number; }
interface DatasetState {
  selectedId: string | null;
  datasets: Dataset[];
  setSelected: (id: string | null) => void;
  setDatasets: (d: Dataset[]) => void;
}

export const useDatasetStore = create<DatasetState>()((set) => ({
  selectedId: null,
  datasets: [],
  setSelected: (id) => set({ selectedId: id }),
  setDatasets: (datasets) => set({ datasets }),
}));
