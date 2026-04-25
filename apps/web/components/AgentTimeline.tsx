"use client";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen,
  Building2,
  Wand2,
  TestTube2,
  ScrollText,
  CheckCircle2,
  Loader2,
  Circle,
  XCircle,
} from "lucide-react";
import type { AgentState } from "@/lib/types";

const ICONS = {
  reader: BookOpen,
  architect: Building2,
  migrator: Wand2,
  tester: TestTube2,
  documenter: ScrollText,
};

const STATUS_ICONS = {
  idle: Circle,
  running: Loader2,
  complete: CheckCircle2,
  error: XCircle,
};

const TIER_BADGE = {
  super: "bg-violet-500/15 text-violet-300 border-violet-500/40",
  nano: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  "super+nano": "bg-amber-500/15 text-amber-300 border-amber-500/40",
};

interface Props {
  agents: AgentState[];
  thinking?: { agent: string; text: string };
}

export function AgentTimeline({ agents, thinking }: Props) {
  return (
    <div className="relative space-y-2">
      <div className="absolute left-[27px] top-2 bottom-2 w-px bg-slate-800" />
      {agents.map((agent, idx) => {
        const Icon = ICONS[agent.name];
        const StatusIcon = STATUS_ICONS[agent.status];
        const isLive = thinking?.agent === agent.name && agent.status === "running";

        return (
          <motion.div
            key={agent.name}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            className="relative flex gap-4"
          >
            <div
              className={`relative z-10 flex h-14 w-14 shrink-0 items-center justify-center rounded-full border-2 transition-all ${
                agent.status === "complete"
                  ? "border-nvidia bg-nvidia/10"
                  : agent.status === "running"
                  ? "border-nvidia bg-nvidia/5 nvidia-glow"
                  : agent.status === "error"
                  ? "border-red-500/60 bg-red-500/10"
                  : "border-slate-700 bg-slate-900"
              }`}
            >
              <Icon
                className={`h-6 w-6 transition-colors ${
                  agent.status === "complete" || agent.status === "running"
                    ? "text-nvidia"
                    : "text-slate-500"
                }`}
              />
            </div>

            <div className="flex-1 pb-4">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-semibold text-slate-100">{agent.label}</h3>
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wide ${
                    TIER_BADGE[agent.tier]
                  }`}
                >
                  {agent.tier}
                </span>
                <StatusIcon
                  className={`h-4 w-4 ${
                    agent.status === "running" ? "animate-spin text-nvidia" : ""
                  } ${agent.status === "complete" ? "text-nvidia" : ""} ${
                    agent.status === "error" ? "text-red-400" : ""
                  } ${agent.status === "idle" ? "text-slate-600" : ""}`}
                />
              </div>
              <p className="mt-0.5 text-xs text-slate-500">{agent.description}</p>
              {agent.summary && (
                <p className="mt-1.5 text-sm text-slate-300">{agent.summary}</p>
              )}

              <AnimatePresence>
                {isLive && thinking && thinking.text && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-2 max-h-32 overflow-y-auto rounded-md border border-nvidia/30 bg-slate-950/60 p-3 font-mono text-xs leading-relaxed text-nvidia/90 scrollbar-thin"
                  >
                    {thinking.text}
                    <span className="ml-1 inline-block h-3 w-1.5 animate-pulse bg-nvidia" />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
