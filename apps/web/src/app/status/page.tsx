"use client";

import { useEffect, useState } from "react";

import { apiUrl } from "@/lib/api";

interface HealthData {
  status: string;
  services: Record<string, string>;
}

function StatusBadge({ value }: { value: string }) {
  const isOk = value === "ok";
  return (
    <span
      className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${
        isOk
          ? "bg-emerald-900/50 text-emerald-400"
          : "bg-red-900/50 text-red-400"
      }`}
    >
      {value}
    </span>
  );
}

export default function StatusPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const res = await fetch(apiUrl("/api/health"));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setHealth(await res.json());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "연결 실패");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const id = setInterval(fetchHealth, 10_000);
    return () => clearInterval(id);
  }, []);

  return (
    <main className="mx-auto max-w-5xl">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-bold">시스템 상태</h1>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="rounded-lg bg-neutral-800 px-4 py-2 text-sm transition hover:bg-neutral-700 disabled:opacity-50"
        >
          {loading ? "확인 중..." : "새로고침"}
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-lg bg-red-900/30 p-4 text-red-400">
          API 서버에 연결할 수 없습니다: {error}
        </div>
      )}

      {health && (
        <div className="mb-6 flex items-center gap-3">
          <span className="text-sm text-neutral-400">전체 상태:</span>
          <StatusBadge value={health.status} />
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {(
          [
            { key: "api", label: "API Server", desc: "FastAPI :8000" },
            { key: "postgres", label: "PostgreSQL", desc: "Database :5432" },
            { key: "redis", label: "Redis", desc: "Job Queue :6379" },
            { key: "minio", label: "MinIO", desc: "Object Storage :9000" },
          ] as const
        ).map(({ key, label, desc }) => (
          <div
            key={key}
            className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5"
          >
            <div className="mb-1 flex items-center justify-between">
              <span className="font-medium">{label}</span>
              {health?.services?.[key] ? (
                <StatusBadge value={health.services[key]} />
              ) : loading ? (
                <span className="text-xs text-neutral-500">...</span>
              ) : (
                <StatusBadge value="unreachable" />
              )}
            </div>
            <p className="text-sm text-neutral-500">{desc}</p>
          </div>
        ))}

        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
          <div className="mb-1 flex items-center justify-between">
            <span className="font-medium">Worker</span>
            {health?.services?.redis === "ok" ? (
              <StatusBadge value="ok" />
            ) : loading ? (
              <span className="text-xs text-neutral-500">...</span>
            ) : (
              <StatusBadge value="unknown" />
            )}
          </div>
          <p className="text-sm text-neutral-500">arq Worker (via Redis)</p>
        </div>

        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5">
          <div className="mb-1 flex items-center justify-between">
            <span className="font-medium">Web</span>
            <StatusBadge value="ok" />
          </div>
          <p className="text-sm text-neutral-500">Next.js :3000</p>
        </div>
      </div>
    </main>
  );
}
