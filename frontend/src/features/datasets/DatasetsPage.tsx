import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Database, Trash2, Eye, FileText, Sparkles, X } from "lucide-react";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { AIThinking } from "@/components/ui/ai-thinking";
import { DatasetProfileReveal } from "@/components/dataset/DatasetProfileReveal";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useToast } from "@/components/Toast";
import { datasetsApi } from "@/lib/api";
import { useDatasetStore } from "@/store/dataset";
import { fmtDate, truncate } from "@/lib/utils";

const ACCEPTED_EXTENSIONS = [".csv", ".xlsx", ".xls", ".json"];

export default function DatasetsPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const { setDatasets, setSelected } = useDatasetStore();
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [reveal, setReveal] = useState<any | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["datasets"],
    queryFn: async () => {
      const r = await datasetsApi.list();
      const list = r.data.items ?? r.data.datasets ?? r.data ?? [];
      setDatasets(list);
      return list;
    },
  });

  const deleteMut = useMutation({
    mutationFn: datasetsApi.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["datasets"] });
      toast({ title: "Dataset deleted", variant: "success" });
    },
    onError: () => {
      toast({ title: "Couldn't delete dataset", description: "Please try again.", variant: "error" });
    },
  });

  const uploadMut = useMutation({
    mutationFn: (file: File) => datasetsApi.upload(file),
    onSuccess: async (res, file) => {
      setUploadedFileName(file.name);
      // Show the AI reveal only when the profiler actually produced
      // something meaningful -- an empty/failed profile just falls
      // through to the normal list, no broken reveal card.
      const profile = res.data?.column_profile;
      if (profile && profile.row_count > 0) {
        setReveal(profile);
      } else {
        toast({ title: "Dataset uploaded", description: file.name, variant: "success" });
      }
      await qc.invalidateQueries({ queryKey: ["datasets"] });
      if (res.data?.id) setSelected(res.data.id);
    },
    onError: (_err, file) => {
      toast({
        title: "Upload failed",
        description: `Couldn't process ${file.name}. Check the file format and try again.`,
        variant: "error",
      });
    },
  });

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) uploadMut.mutate(f);
  };

  const datasets = data ?? [];

  return (
    <PageWrapper title="Datasets" subtitle="Upload any business dataset — Kairos figures out the rest">
      <AnimatePresence mode="wait">
        {reveal ? (
          <motion.div key="reveal" exit={{ opacity: 0, y: -8 }} className="relative">
            <button
              onClick={() => setReveal(null)}
              className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-muted hover:bg-accent flex items-center justify-center z-10"
              title="Dismiss"
            >
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
            <DatasetProfileReveal
              profile={reveal}
              fileName={uploadedFileName ?? "your file"}
              onContinue={() => setReveal(null)}
            />
          </motion.div>
        ) : (
          <motion.div key="upload" className="grid grid-cols-3 gap-6">
            {/* Upload zone -- no dataset type selection. Ever. The AI
                figures out what the data is after looking at it, the same
                way you don't tell ChatGPT what kind of PDF you're about
                to upload. */}
            <div className="col-span-1 space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Upload Dataset</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <motion.div
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={onDrop}
                    onClick={() => fileRef.current?.click()}
                    animate={{
                      borderColor: dragOver ? "hsl(217 91% 60%)" : "hsl(217 20% 16%)",
                      scale: dragOver ? 1.01 : 1,
                    }}
                    className="border-2 border-dashed border-border rounded-xl p-8 flex flex-col items-center gap-3 cursor-pointer hover:border-primary/40 hover:bg-primary/5 transition-colors"
                  >
                    {uploadMut.isPending ? (
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
                      >
                        <Sparkles className="h-8 w-8 text-primary" />
                      </motion.div>
                    ) : (
                      <Upload className="h-8 w-8 text-muted-foreground" />
                    )}
                    <div className="text-center">
                      <p className="text-xs font-medium text-foreground">
                        {uploadMut.isPending ? "AI is analyzing your dataset…" : "Drop CSV, Excel or JSON"}
                      </p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {uploadMut.isPending ? "Detecting structure, domain, and key columns" : "or click to browse"}
                      </p>
                    </div>
                    <input
                      ref={fileRef}
                      type="file"
                      accept={ACCEPTED_EXTENSIONS.join(",")}
                      className="hidden"
                      onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadMut.mutate(f); }}
                    />
                  </motion.div>

                  <div className="space-y-1 pt-1">
                    {["Any business domain — Sales, HR, Finance, Healthcare…", "CSV, Excel (.xlsx), or JSON", "Structure detected automatically", "Up to 100 MB"].map((f) => (
                      <div key={f} className="flex items-center gap-1.5">
                        <Sparkles className="h-3 w-3 text-primary/60 shrink-0" />
                        <span className="text-[10px] text-muted-foreground">{f}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Dataset list */}
            <div className="col-span-2">
              <Card className="h-full">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{datasets.length} Dataset{datasets.length !== 1 ? "s" : ""}</CardTitle>
                    <Badge variant="primary">{datasets.length} total</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  {isLoading ? (
                    <div className="space-y-3">
                      {[...Array(3)].map((_, i) => (
                        <div key={i} className="h-16 rounded-xl bg-muted animate-pulse" />
                      ))}
                    </div>
                  ) : datasets.length === 0 ? (
                    <EmptyState
                      icon={Database}
                      title="No datasets yet"
                      description="Upload any CSV, Excel, or JSON file — Kairos will detect its structure, business domain, and key columns automatically. No setup required."
                    />
                  ) : (
                    <AnimatePresence>
                      <div className="space-y-2">
                        {datasets.map((d: any, i: number) => (
                          <motion.div
                            key={d.id}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 8 }}
                            transition={{ delay: i * 0.04 }}
                            whileHover={{ x: 2 }}
                            className="flex items-center gap-3 p-3.5 rounded-xl border border-border hover:border-primary/30 hover:bg-accent transition-colors group"
                          >
                            <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                              <FileText className="h-5 w-5 text-primary" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-foreground truncate">{d.name}</p>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-[10px] text-muted-foreground">
                                  {d.domain_guess ?? "General Business Data"}
                                </span>
                                <span className="text-[10px] text-muted-foreground">·</span>
                                <span className="text-[10px] text-muted-foreground">{fmtDate(d.created_at)}</span>
                                {d.row_count ? (
                                  <>
                                    <span className="text-[10px] text-muted-foreground">·</span>
                                    <span className="text-[10px] text-muted-foreground">{d.row_count.toLocaleString()} rows</span>
                                  </>
                                ) : null}
                              </div>
                            </div>
                            <Badge variant={d.status === "valid" ? "success" : "default"}>{d.status}</Badge>
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <Button variant="ghost" size="icon-sm" onClick={() => setSelected(d.id)} title="Select">
                                <Eye className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => setPendingDelete({ id: d.id, name: d.name })}
                                className="hover:text-destructive"
                                title="Delete"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </AnimatePresence>
                  )}
                </CardContent>
              </Card>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <ConfirmDialog
        open={!!pendingDelete}
        onOpenChange={(open) => { if (!open) setPendingDelete(null); }}
        title="Delete this dataset?"
        description={pendingDelete ? `"${pendingDelete.name}" and all analyses built on it will be permanently removed. This can't be undone.` : ""}
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => { if (pendingDelete) deleteMut.mutate(pendingDelete.id); }}
      />
    </PageWrapper>
  );
}
