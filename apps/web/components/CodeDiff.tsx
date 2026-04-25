"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import type { MigratedFile } from "@/lib/types";
import { FileCode2, ChevronDown } from "lucide-react";

const DiffEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.DiffEditor),
  { ssr: false, loading: () => <div className="p-6 text-slate-500">Loading editor…</div> },
);

interface Props {
  files: MigratedFile[];
  sourceLanguage?: string;
  targetLanguage?: string;
  getOriginal?: (sourcePath: string) => string;
}

export function CodeDiff({
  files,
  sourceLanguage = "cobol",
  targetLanguage = "python",
  getOriginal,
}: Props) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [isOpen, setIsOpen] = useState(true);

  if (files.length === 0) {
    return (
      <div className="flex h-full items-center justify-center rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-slate-500">
        <div className="text-center">
          <FileCode2 className="mx-auto h-10 w-10 opacity-40" />
          <p className="mt-3 text-sm">Migrated code will appear here as agents complete</p>
        </div>
      </div>
    );
  }

  const active = files[activeIdx];
  const original = getOriginal?.(active.source) ?? "";

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-800 bg-slate-950/40 overflow-hidden">
      <div className="border-b border-slate-800 bg-slate-900/60">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex w-full items-center justify-between px-4 py-2.5 text-left"
        >
          <div className="flex items-center gap-2">
            <FileCode2 className="h-4 w-4 text-nvidia" />
            <span className="text-sm font-medium text-slate-200">
              {active.source} → {active.target}
            </span>
            <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
              {(active.confidence * 100).toFixed(0)}% confidence
            </span>
            {active.warnings.length > 0 && (
              <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] text-amber-300">
                {active.warnings.length} warning{active.warnings.length > 1 ? "s" : ""}
              </span>
            )}
          </div>
          <ChevronDown
            className={`h-4 w-4 text-slate-500 transition-transform ${isOpen ? "" : "-rotate-90"}`}
          />
        </button>
        {files.length > 1 && (
          <div className="flex gap-1 border-t border-slate-800 px-2 py-1.5 overflow-x-auto scrollbar-thin">
            {files.map((f, i) => (
              <button
                key={f.target}
                onClick={() => setActiveIdx(i)}
                className={`whitespace-nowrap rounded-md px-2 py-1 text-xs transition-colors ${
                  i === activeIdx
                    ? "bg-nvidia/15 text-nvidia"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                }`}
              >
                {f.target.split("/").pop()}
              </button>
            ))}
          </div>
        )}
      </div>

      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="relative flex-1 min-h-[420px]"
        >
          <DiffEditor
            height="100%"
            theme="vs-dark"
            original={original}
            modified={active.code}
            originalLanguage={sourceLanguage}
            modifiedLanguage={targetLanguage}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              renderSideBySide: true,
              fontSize: 12,
              lineNumbers: "on",
            }}
          />
        </motion.div>
      )}

      {active.warnings.length > 0 && (
        <div className="border-t border-amber-500/30 bg-amber-500/5 px-4 py-2 text-xs">
          <div className="font-medium text-amber-300">Migration warnings:</div>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-amber-200/80">
            {active.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
