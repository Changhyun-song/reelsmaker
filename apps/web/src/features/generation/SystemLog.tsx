"use client";

import { useRef, useEffect } from "react";

export interface LogEntry {
  timestamp: number;
  level: "info" | "success" | "warn" | "error";
  message: string;
}

interface SystemLogProps {
  logs: LogEntry[];
  maxHeight?: string;
}

const LEVEL_STYLES: Record<string, string> = {
  info: "text-neutral-400",
  success: "text-emerald-400",
  warn: "text-amber-400",
  error: "text-red-400",
};

const LEVEL_PREFIX: Record<string, string> = {
  info: "INFO",
  success: "DONE",
  warn: "WARN",
  error: "FAIL",
};

function formatTs(ms: number): string {
  const d = new Date(ms);
  return d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export default function SystemLog({ logs, maxHeight = "max-h-48" }: SystemLogProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  if (logs.length === 0) return null;

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950/80 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-800">
        <span className="text-[11px] font-semibold text-neutral-500">SYSTEM</span>
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
      </div>
      <div className={`${maxHeight} overflow-y-auto px-4 py-2 space-y-0.5 font-mono`}>
        {logs.map((log, i) => (
          <div key={i} className="flex gap-2 text-[11px] leading-5">
            <span className="text-neutral-600 shrink-0">{formatTs(log.timestamp)}</span>
            <span className={`shrink-0 font-bold ${LEVEL_STYLES[log.level]}`}>
              {LEVEL_PREFIX[log.level]}
            </span>
            <span className={LEVEL_STYLES[log.level]}>{log.message}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
