"use client";
import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Linkedin, Cpu } from "lucide-react";

import { NemotronBadge } from "@/components/NemotronBadge";
import { FileUpload } from "@/components/FileUpload";
import { AgentTimeline } from "@/components/AgentTimeline";
import { CodeDiff } from "@/components/CodeDiff";
import { MetricsCard } from "@/components/MetricsCard";
import { ReportPanel } from "@/components/ReportPanel";

import {
  fetchSample,
  streamMigrationFromUpload,
  streamSampleMigration,
} from "@/lib/api";
import type {
  AgentName,
  AgentState,
  MigratedFile,
  NemotronMetrics,
  SSEEvent,
} from "@/lib/types";

const DEFAULT_AGENTS: AgentState[] = [
  {
    name: "reader",
    label: "Reader",
    tier: "nano",
    description: "Parses source, extracts AST, identifies dependencies",
    status: "idle",
  },
  {
    name: "architect",
    label: "Architect",
    tier: "super",
    description: "1M-context reasoning · designs target architecture",
    status: "idle",
  },
  {
    name: "migrator",
    label: "Migrator",
    tier: "nano",
    description: "Converts file by file, in parallel",
    status: "idle",
  },
  {
    name: "tester",
    label: "Tester",
    tier: "super+nano",
    description: "Super designs strategy · Nano writes test cases",
    status: "idle",
  },
  {
    name: "documenter",
    label: "Documenter",
    tier: "nano",
    description: "Synthesizes the migration report",
    status: "idle",
  },
];

export default function HomePage() {
  const [agents, setAgents] = useState<AgentState[]>(DEFAULT_AGENTS);
  const [thinking, setThinking] = useState<{ agent: string; text: string }>({
    agent: "",
    text: "",
  });
  const [metrics, setMetrics] = useState<NemotronMetrics | null>(null);
  const [files, setFiles] = useState<MigratedFile[]>([]);
  const [report, setReport] = useState<{ title: string; markdown: string } | null>(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState<string>("");
  const [originals, setOriginals] = useState<Record<string, string>>({});
  const [errorMsg, setErrorMsg] = useState<string>("");

  const reset = () => {
    setAgents(DEFAULT_AGENTS.map((a) => ({ ...a })));
    setThinking({ agent: "", text: "" });
    setMetrics(null);
    setFiles([]);
    setReport(null);
    setProgress(0);
    setProgressMessage("");
    setErrorMsg("");
  };

  const updateAgent = (name: AgentName, patch: Partial<AgentState>) => {
    setAgents((prev) => prev.map((a) => (a.name === name ? { ...a, ...patch } : a)));
  };

  const handleEvent = (e: SSEEvent) => {
    switch (e.type) {
      case "progress": {
        if (typeof e.percent === "number") setProgress(e.percent);
        if (e.message) setProgressMessage(e.message);
        if (e.step && DEFAULT_AGENTS.some((a) => a.name === e.step)) {
          // Mark the current step as running, prior steps complete.
          setAgents((prev) => {
            const idx = prev.findIndex((a) => a.name === e.step);
            return prev.map((a, i) => {
              if (i < idx) return a.status === "complete" ? a : { ...a, status: "complete" };
              if (i === idx) return { ...a, status: "running" };
              return a;
            });
          });
        }
        break;
      }
      case "agent_thinking":
        if (e.agent) {
          setThinking((prev) => ({
            agent: e.agent!,
            text: prev.agent === e.agent ? prev.text + (e.delta ?? "") : e.delta ?? "",
          }));
        }
        break;
      case "agent_complete": {
        if (!e.agent) break;
        const data = (e.data ?? {}) as Record<string, unknown>;
        let summary = e.summary ?? "";
        if (e.agent === "reader") {
          const modules = (data.modules as string[] | undefined)?.length ?? 0;
          summary = `${data.total_files ?? 0} files · ${data.total_lines ?? 0} lines · ${modules} modules · ${data.complexity ?? "?"} complexity`;
        } else if (e.agent === "architect") {
          summary = `Target: ${data.framework ?? "?"} · ${data.files_planned ?? 0} files planned · ${data.estimated_effort_hours ?? "?"}h estimated`;
          const rationale = (data.rationale as string | undefined) ?? "";
          if (rationale) {
            setThinking({ agent: "architect", text: rationale });
          }
        } else if (e.agent === "migrator") {
          summary = `${data.files_migrated ?? 0} files migrated`;
          const migrated = (data.files as MigratedFile[] | undefined) ?? [];
          if (migrated.length) setFiles(migrated);
        } else if (e.agent === "tester") {
          const cov = ((data.coverage as number | undefined) ?? 0) * 100;
          summary = `${data.test_files ?? 0} test files · ~${cov.toFixed(0)}% coverage`;
        } else if (e.agent === "documenter") {
          summary = `Report ready: ${data.title ?? "Migration report"}`;
          setReport({
            title: (data.title as string) ?? "Migration report",
            markdown: (data.markdown as string) ?? "",
          });
        }
        updateAgent(e.agent as AgentName, { status: "complete", summary, data });
        break;
      }
      case "metrics":
        if (e.metrics) setMetrics(e.metrics);
        break;
      case "complete":
        setRunning(false);
        setProgress(100);
        setAgents((prev) => prev.map((a) => ({ ...a, status: "complete" })));
        break;
      case "error":
        setRunning(false);
        setErrorMsg(e.message ?? "Pipeline failed");
        setAgents((prev) =>
          prev.map((a) => (a.status === "running" ? { ...a, status: "error" } : a)),
        );
        break;
    }
  };

  const startUpload = async (uploaded: File[]) => {
    reset();
    setRunning(true);
    // Capture originals for the diff view.
    const map: Record<string, string> = {};
    await Promise.all(
      uploaded.map(async (f) => {
        map[f.name] = await f.text();
      }),
    );
    setOriginals(map);
    try {
      await streamMigrationFromUpload(uploaded, "python", handleEvent, () =>
        setRunning(false),
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setRunning(false);
    }
  };

  const startSample = async () => {
    reset();
    setRunning(true);
    try {
      const sample = await fetchSample();
      const map: Record<string, string> = {};
      for (const f of sample.files) {
        // Only previews are available from /api/sample, so re-fetch full source
        // by reading from the API's static-served files isn't done here; instead we
        // store the preview which Monaco diff will show as the "before".
        map[f.path] = f.preview;
      }
      setOriginals(map);
    } catch {
      // non-fatal; diff view will just show empty original
    }
    try {
      await streamSampleMigration("python", handleEvent, () => setRunning(false));
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
      setRunning(false);
    }
  };

  const getOriginal = (sourcePath: string) => {
    // Match by full path or basename.
    if (originals[sourcePath]) return originals[sourcePath];
    const base = sourcePath.split("/").pop() ?? sourcePath;
    return originals[base] ?? "";
  };

  const headerProgressBar = useMemo(
    () => (running ? Math.max(progress, 2) : progress),
    [running, progress],
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 md:py-12">
      {/* Top progress bar */}
      <AnimatePresence>
        {running && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed left-0 right-0 top-0 z-50 h-1 bg-slate-800"
          >
            <motion.div
              className="h-full bg-nvidia"
              animate={{ width: `${headerProgressBar}%` }}
              transition={{ ease: "easeInOut", duration: 0.4 }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <header className="mb-10 flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-3">
            <Cpu className="h-8 w-8 text-nvidia" />
            <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
              CodeMigrator <span className="text-nvidia">AI</span>
            </h1>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Multi-agent legacy code migration · Super + Nano routing
          </p>
        </div>
        <NemotronBadge size="lg" />
      </header>

      {/* Metrics strip (always visible once we have data) */}
      {metrics && (
        <section className="mb-8">
          <MetricsCard metrics={metrics} />
        </section>
      )}

      {/* Upload (collapses when running) */}
      {!running && files.length === 0 && (
        <motion.section
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mb-8 rounded-2xl border border-slate-800 bg-slate-900/40 p-6"
        >
          <h2 className="text-lg font-semibold text-slate-100">Upload legacy code</h2>
          <p className="mt-1 text-sm text-slate-400">
            COBOL → Python migration in 5 agents. Watch Super reason about the architecture
            while Nano handles the high-throughput conversion.
          </p>
          <div className="mt-4">
            <FileUpload onFiles={startUpload} onUseSample={startSample} disabled={running} />
          </div>
        </motion.section>
      )}

      {errorMsg && (
        <div className="mb-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
          <strong>Error:</strong> {errorMsg}
        </div>
      )}

      {/* Main split pane */}
      {(running || files.length > 0 || progress > 0) && (
        <section className="grid gap-6 lg:grid-cols-[400px_1fr]">
          {/* Left: agent timeline */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-100">Agent pipeline</h2>
              <span className="text-xs text-slate-500">{progressMessage}</span>
            </div>
            <AgentTimeline agents={agents} thinking={thinking} />
          </div>

          {/* Right: code diff + report */}
          <div className="space-y-6">
            <CodeDiff files={files} getOriginal={getOriginal} />
            {report && <ReportPanel title={report.title} markdown={report.markdown} />}
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="mt-16 border-t border-slate-800 pt-6 text-center">
        <div className="flex flex-col items-center justify-between gap-3 text-xs text-slate-500 md:flex-row">
          <div>
            Built by <span className="font-semibold text-slate-300">Ritish Kurma</span>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="https://www.linkedin.com/in/ritish-kurma/"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 hover:text-nvidia"
            >
              <Linkedin className="h-3.5 w-3.5" />
              LinkedIn
            </a>
          </div>
          <div className="rounded-full border border-nvidia/30 px-3 py-1 text-nvidia">
            NVIDIA Nemotron 3 Workshop · IIIT Hyderabad · May 16 2026
          </div>
        </div>
      </footer>
    </main>
  );
}
