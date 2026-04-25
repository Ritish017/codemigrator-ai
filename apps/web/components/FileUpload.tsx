"use client";
import { Upload, FileCode, Sparkles } from "lucide-react";
import { useRef, useState } from "react";
import { motion } from "framer-motion";

interface Props {
  onFiles: (files: File[]) => void;
  onUseSample: () => void;
  disabled?: boolean;
}

export function FileUpload({ onFiles, onUseSample, disabled }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (list: FileList | null) => {
    if (!list || list.length === 0) return;
    onFiles(Array.from(list));
  };

  return (
    <div className="space-y-4">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (!disabled) handleFiles(e.dataTransfer.files);
        }}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`group relative cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-all ${
          dragOver ? "border-nvidia bg-nvidia/5" : "border-slate-700 hover:border-slate-500"
        } ${disabled ? "pointer-events-none opacity-50" : ""}`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".cbl,.cob,.cobol,.cpy,.zip,.f,.f90,.pli"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <Upload className="mx-auto h-10 w-10 text-slate-400 transition-colors group-hover:text-nvidia" />
        <div className="mt-3 text-sm font-medium text-slate-200">
          Drop COBOL files here, or click to browse
        </div>
        <div className="mt-1 text-xs text-slate-500">
          .cbl · .cob · .cpy · .zip — up to ~50 files for the free tier
        </div>
      </motion.div>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-800" />
        <span className="text-xs uppercase tracking-wider text-slate-500">or</span>
        <div className="h-px flex-1 bg-slate-800" />
      </div>

      <button
        onClick={onUseSample}
        disabled={disabled}
        className="group flex w-full items-center justify-center gap-2 rounded-xl bg-nvidia px-6 py-4 font-semibold text-slate-950 shadow-lg shadow-nvidia/20 transition-all hover:bg-nvidia-light hover:shadow-nvidia/40 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Sparkles className="h-5 w-5 transition-transform group-hover:rotate-12" />
        Try Sample COBOL Banking
        <FileCode className="h-5 w-5" />
      </button>
      <p className="text-center text-xs text-slate-500">
        3 enterprise programs: ACCOUNT.cbl · TRANSACT.cbl · INTEREST.cbl
      </p>
    </div>
  );
}
