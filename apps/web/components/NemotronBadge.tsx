"use client";
import { motion } from "framer-motion";

export function NemotronBadge({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const padding = size === "lg" ? "px-4 py-2" : size === "sm" ? "px-2 py-1" : "px-3 py-1.5";
  const text = size === "lg" ? "text-base" : size === "sm" ? "text-xs" : "text-sm";
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`inline-flex items-center gap-2 rounded-full border border-nvidia/40 bg-nvidia/10 ${padding} ${text} font-medium text-nvidia`}
    >
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-nvidia opacity-75"></span>
        <span className="relative inline-flex h-2 w-2 rounded-full bg-nvidia"></span>
      </span>
      Powered by NVIDIA Nemotron 3
    </motion.div>
  );
}
