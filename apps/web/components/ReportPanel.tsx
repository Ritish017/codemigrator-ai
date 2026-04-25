"use client";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ScrollText } from "lucide-react";

interface Props {
  title?: string;
  markdown: string;
}

export function ReportPanel({ title, markdown }: Props) {
  if (!markdown) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-slate-800 bg-slate-900/40"
    >
      <div className="flex items-center gap-2 border-b border-slate-800 px-5 py-3">
        <ScrollText className="h-4 w-4 text-nvidia" />
        <h3 className="text-sm font-semibold text-slate-100">
          {title ?? "Migration report"}
        </h3>
      </div>
      <div className="prose prose-invert prose-sm max-w-none p-6 prose-headings:text-slate-100 prose-strong:text-slate-100 prose-code:text-nvidia prose-code:bg-slate-950/60 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-th:text-slate-200">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
      </div>
    </motion.div>
  );
}
