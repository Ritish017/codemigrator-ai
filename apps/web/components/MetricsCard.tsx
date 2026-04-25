"use client";
import { motion } from "framer-motion";
import { Activity, DollarSign, Cpu, Zap, Gauge } from "lucide-react";
import type { NemotronMetrics } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

interface Props {
  metrics: NemotronMetrics | null;
}

const FALLBACK: NemotronMetrics = {
  total_tokens: 0,
  total_cost_usd: 0,
  super_calls: 0,
  nano_calls: 0,
  super_tokens: 0,
  nano_tokens: 0,
  nano_routing_percent: 0,
  avg_latency_super_s: 0,
  avg_latency_nano_s: 0,
};

export function MetricsCard({ metrics }: Props) {
  const m = metrics ?? FALLBACK;
  const totalCalls = m.super_calls + m.nano_calls;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      <Stat
        icon={<Activity className="h-4 w-4 text-nvidia" />}
        label="Tokens used"
        value={formatNumber(m.total_tokens)}
        sub={`${formatNumber(m.super_tokens)} super · ${formatNumber(m.nano_tokens)} nano`}
      />
      <Stat
        icon={<DollarSign className="h-4 w-4 text-emerald-400" />}
        label="Total calls"
        value={formatNumber(totalCalls)}
        sub="free tier"
      />
      <Stat
        icon={<Cpu className="h-4 w-4 text-violet-400" />}
        label="Super (120B) calls"
        value={formatNumber(m.super_calls)}
        sub={`${m.avg_latency_super_s.toFixed(1)}s avg`}
      />
      <Stat
        icon={<Zap className="h-4 w-4 text-emerald-400" />}
        label="Nano (30B) calls"
        value={formatNumber(m.nano_calls)}
        sub={`${m.avg_latency_nano_s.toFixed(1)}s avg`}
      />
      <Stat
        icon={<Gauge className="h-4 w-4 text-nvidia" />}
        label="Routed to Nano"
        value={`${m.nano_routing_percent.toFixed(0)}%`}
        sub="cheap + fast tier"
        accent
      />
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl border p-4 ${
        accent ? "border-nvidia/40 bg-nvidia/5" : "border-slate-800 bg-slate-900/40"
      }`}
    >
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
        {icon}
        {label}
      </div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${accent ? "text-nvidia" : "text-slate-100"}`}>
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </motion.div>
  );
}
