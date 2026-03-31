"use client";

import { useEffect, useState, useCallback } from "react";
import { apiUrl } from "@/lib/api";
import ReleaseChecklist from "@/features/release-check/ReleaseChecklist";

/* ── Types ──────────────────────────────────────────── */

interface ConnInfo {
  status: string;
  error?: string;
  bucket?: string;
}

interface ProviderInfo {
  provider: string;
  mode: string;
  api_key_set: boolean | null;
}

interface WorkerInfo {
  status: string;
  recent_completed?: number;
  stuck_queued?: number;
}

interface DiagEntry {
  code: string;
  message: string;
  hint?: string;
}

interface DiagData {
  overall: string;
  is_production: boolean;
  errors: DiagEntry[];
  warnings: DiagEntry[];
  connectivity: Record<string, ConnInfo>;
  providers: Record<string, ProviderInfo>;
  worker: WorkerInfo;
  environment: {
    debug: boolean;
    cors_origins: string[];
    s3_public_endpoint_set: boolean;
    auth_enabled: boolean;
  };
  required_env: Record<string, boolean>;
  error_count: number;
  warning_count: number;
}

/* ── Helpers ─────────────────────────────────────────── */

function relTime(iso: string | null): string {
  if (!iso) return "";
  const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (sec < 60) return `${sec}초 전`;
  if (sec < 3600) return `${Math.floor(sec / 60)}분 전`;
  return `${Math.floor(sec / 3600)}시간 전`;
}

/* ── Sub-components ──────────────────────────────────── */

function ConnCard({ name, label, icon, info, desc }: {
  name: string; label: string; icon: string; info: ConnInfo | undefined; desc: string;
}) {
  const ok = info?.status === "ok";
  return (
    <div className={`rounded-xl border p-4 ${
      ok ? "border-emerald-800/40 bg-emerald-950/10" : "border-red-800/40 bg-red-950/10"
    }`}>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span>{icon}</span>
          <span className="font-medium text-sm">{label}</span>
        </div>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
          ok ? "bg-emerald-600/20 text-emerald-400" : "bg-red-600/20 text-red-400"
        }`}>
          {ok ? "연결됨" : "오류"}
        </span>
      </div>
      <p className="text-xs text-neutral-500 mb-1">{desc}</p>
      {info?.error && (
        <p className="text-[10px] text-red-400/70 mt-1 line-clamp-2">{info.error}</p>
      )}
    </div>
  );
}

function ProviderCard({ name, info }: { name: string; info: ProviderInfo }) {
  const isMock = info.mode === "mock";
  const hasKey = info.api_key_set;
  const isDown = info.mode === "unavailable" || (!isMock && hasKey === false);

  return (
    <div className={`rounded-xl border p-4 ${
      isMock ? "border-amber-800/40 bg-amber-950/10"
      : isDown ? "border-red-800/40 bg-red-950/10"
      : "border-emerald-800/40 bg-emerald-950/10"
    }`}>
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium text-sm capitalize">{name}</span>
        {isMock ? (
          <span className="rounded-full bg-amber-600/20 text-amber-400 px-2.5 py-0.5 text-xs font-bold">
            테스트 모드
          </span>
        ) : isDown ? (
          <span className="rounded-full bg-red-600/20 text-red-400 px-2.5 py-0.5 text-xs font-bold">
            키 없음
          </span>
        ) : (
          <span className="rounded-full bg-emerald-600/20 text-emerald-400 px-2.5 py-0.5 text-xs font-bold">
            활성
          </span>
        )}
      </div>
      <p className="text-xs text-neutral-500">
        {info.provider}
        {isMock && " — 실제 AI 호출 없이 더미 데이터를 반환합니다"}
        {!isMock && hasKey === false && " — API 키를 설정하세요"}
      </p>
    </div>
  );
}

/* ── Main ────────────────────────────────────────────── */

export default function StatusPage() {
  const [data, setData] = useState<DiagData | null>(null);
  const [webApiOk, setWebApiOk] = useState<boolean | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);

  const fetchDiag = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(apiUrl("/api/diagnostics"));
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setData(await r.json());
      setWebApiOk(true);
      setFetchError(null);
    } catch (e) {
      setWebApiOk(false);
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("fetch") || msg.includes("Failed") || msg.includes("NetworkError")) {
        setFetchError("Web → API 연결 실패. NEXT_PUBLIC_API_URL과 CORS 설정을 확인하세요.");
      } else {
        setFetchError(`API 오류: ${msg}`);
      }
    } finally {
      setLoading(false);
      setLastRefresh(new Date().toISOString());
    }
  }, []);

  useEffect(() => {
    fetchDiag();
    const id = setInterval(fetchDiag, 15_000);
    return () => clearInterval(id);
  }, [fetchDiag]);

  const apiUrlValue = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const isLocalApi = apiUrlValue.includes("localhost") || apiUrlValue.includes("127.0.0.1");

  const overallColor = data?.overall === "healthy" ? "text-emerald-400"
    : data?.overall === "degraded" ? "text-amber-400"
    : data?.overall === "unhealthy" ? "text-red-400"
    : "text-neutral-500";

  const overallBg = data?.overall === "healthy" ? "bg-emerald-600/20 border-emerald-700/50"
    : data?.overall === "degraded" ? "bg-amber-600/20 border-amber-700/50"
    : data?.overall === "unhealthy" ? "bg-red-600/20 border-red-700/50"
    : "bg-neutral-800 border-neutral-700";

  const overallLabel = data?.overall === "healthy" ? "정상"
    : data?.overall === "degraded" ? "일부 경고"
    : data?.overall === "unhealthy" ? "문제 발견"
    : "확인 중...";

  return (
    <main className="mx-auto max-w-5xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">시스템 진단</h1>
          <p className="text-sm text-neutral-500 mt-0.5">배포 상태 및 환경 진단</p>
        </div>
        <div className="flex items-center gap-3">
          {lastRefresh && (
            <span className="text-[10px] text-neutral-600">{relTime(lastRefresh)} 갱신</span>
          )}
          <button
            onClick={fetchDiag}
            disabled={loading}
            className="rounded-lg bg-neutral-800 px-4 py-2 text-sm transition hover:bg-neutral-700 disabled:opacity-50"
          >
            {loading ? "확인 중..." : "새로고침"}
          </button>
        </div>
      </div>

      {/* Overall status */}
      <div className={`rounded-xl border p-4 flex items-center justify-between ${overallBg}`}>
        <div className="flex items-center gap-3">
          <span className={`text-2xl font-bold ${overallColor}`}>
            {data?.overall === "healthy" ? "●" : data?.overall === "degraded" ? "▲" : "✖"}
          </span>
          <div>
            <p className={`text-lg font-bold ${overallColor}`}>{overallLabel}</p>
            <p className="text-xs text-neutral-500">
              {data ? `에러 ${data.error_count}건, 경고 ${data.warning_count}건` : "API 응답 대기..."}
              {data?.is_production && " · 프로덕션 환경"}
            </p>
          </div>
        </div>
        <div className="text-right text-xs text-neutral-500">
          <p>API: <code className="text-neutral-400">{apiUrlValue}</code></p>
          {isLocalApi && <p className="text-amber-400 mt-0.5">⚠ localhost 주소</p>}
        </div>
      </div>

      {/* Web → API connection (client-side check) */}
      {webApiOk === false && (
        <div className="rounded-xl border border-red-800/50 bg-red-950/20 p-4 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-red-400 text-lg">✖</span>
            <p className="text-sm font-bold text-red-400">Web → API 연결 실패</p>
          </div>
          <p className="text-xs text-red-300/80">{fetchError}</p>
          <div className="text-xs text-neutral-500 space-y-1 border-t border-red-800/30 pt-2 mt-2">
            <p><strong>확인사항:</strong></p>
            <p>1. <code>NEXT_PUBLIC_API_URL</code>이 올바른 API 주소인지 확인 (현재: <code>{apiUrlValue}</code>)</p>
            <p>2. API 서비스가 실행 중인지 확인</p>
            <p>3. API의 <code>CORS_ORIGINS</code>에 현재 웹 도메인이 포함되어 있는지 확인</p>
            <p>4. Vercel 배포 시 환경변수를 설정한 뒤 <strong>재배포</strong>가 필요합니다 (빌드 시점에 주입됨)</p>
          </div>
        </div>
      )}

      {/* Errors */}
      {data && data.errors.length > 0 && (
        <div className="rounded-xl border border-red-800/50 bg-red-950/10 p-4 space-y-2">
          <p className="text-xs font-bold text-red-400 uppercase tracking-wider">
            에러 ({data.errors.length})
          </p>
          {data.errors.map((err, i) => (
            <div key={i} className="rounded-lg bg-red-950/20 border border-red-900/30 p-3">
              <div className="flex items-start gap-2">
                <span className="text-red-400 text-xs mt-0.5">✖</span>
                <div>
                  <p className="text-sm text-red-300 font-medium">{err.message}</p>
                  {err.hint && <p className="text-xs text-neutral-500 mt-0.5">{err.hint}</p>}
                  <span className="text-[9px] text-neutral-600 font-mono">{err.code}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Warnings */}
      {data && data.warnings.length > 0 && (
        <div className="rounded-xl border border-amber-800/50 bg-amber-950/10 p-4 space-y-2">
          <p className="text-xs font-bold text-amber-400 uppercase tracking-wider">
            경고 ({data.warnings.length})
          </p>
          {data.warnings.map((w, i) => (
            <div key={i} className="rounded-lg bg-amber-950/20 border border-amber-900/30 p-3">
              <div className="flex items-start gap-2">
                <span className="text-amber-400 text-xs mt-0.5">▲</span>
                <div>
                  <p className="text-sm text-amber-300 font-medium">{w.message}</p>
                  {w.hint && <p className="text-xs text-neutral-500 mt-0.5">{w.hint}</p>}
                  <span className="text-[9px] text-neutral-600 font-mono">{w.code}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Connectivity grid */}
      {data && (
        <div>
          <p className="text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">연결 상태</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <ConnCard
              name="web-api" label="Web → API" icon="🌐"
              info={webApiOk ? { status: "ok" } : { status: "error", error: fetchError || undefined }}
              desc={`NEXT_PUBLIC_API_URL: ${apiUrlValue}`}
            />
            <ConnCard
              name="postgres" label="API → PostgreSQL" icon="🗄️"
              info={data.connectivity.postgres}
              desc="DATABASE_URL"
            />
            <ConnCard
              name="redis" label="API → Redis" icon="⚡"
              info={data.connectivity.redis}
              desc="REDIS_URL (Job Queue)"
            />
            <ConnCard
              name="storage" label="API → Object Storage" icon="📦"
              info={data.connectivity.storage}
              desc={`S3_ENDPOINT (bucket: ${data.connectivity.storage?.bucket || "?"})`}
            />
          </div>
        </div>
      )}

      {/* Worker */}
      {data && (
        <div>
          <p className="text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">Worker 상태</p>
          <div className={`rounded-xl border p-4 ${
            data.worker.status === "active" ? "border-emerald-800/40 bg-emerald-950/10"
            : data.worker.status === "idle" ? "border-neutral-800 bg-neutral-900/50"
            : data.worker.status === "possibly_down" ? "border-amber-800/40 bg-amber-950/10"
            : "border-red-800/40 bg-red-950/10"
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span>⚙️</span>
                <span className="font-medium text-sm">arq Worker</span>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                data.worker.status === "active" ? "bg-emerald-600/20 text-emerald-400"
                : data.worker.status === "idle" ? "bg-neutral-700/50 text-neutral-400"
                : data.worker.status === "possibly_down" ? "bg-amber-600/20 text-amber-400"
                : "bg-red-600/20 text-red-400"
              }`}>
                {data.worker.status === "active" ? "활성"
                : data.worker.status === "idle" ? "대기 중"
                : data.worker.status === "possibly_down" ? "응답 없음?"
                : data.worker.status === "redis_unavailable" ? "Redis 없음"
                : "확인 불가"}
              </span>
            </div>
            <p className="text-xs text-neutral-500 mt-1">
              {data.worker.status === "active" && `최근 5분 내 ${data.worker.recent_completed}개 작업 완료`}
              {data.worker.status === "idle" && "최근 5분 내 완료된 작업 없음 (queued 작업도 없음)"}
              {data.worker.status === "possibly_down" && `${data.worker.stuck_queued}개 작업이 5분 이상 대기 중 — Worker 서비스 확인 필요`}
              {data.worker.status === "redis_unavailable" && "Redis 연결 실패로 Worker 상태 확인 불가"}
            </p>
          </div>
        </div>
      )}

      {/* Providers */}
      {data && (
        <div>
          <p className="text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">AI Provider 상태</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {Object.entries(data.providers).map(([name, info]) => (
              <ProviderCard key={name} name={name} info={info} />
            ))}
          </div>
        </div>
      )}

      {/* CORS info */}
      {data && (
        <div>
          <p className="text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">환경 설정</p>
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400">CORS Origins</span>
              <div className="flex gap-1 flex-wrap justify-end">
                {data.environment.cors_origins.map((o, i) => (
                  <code key={i} className="bg-neutral-800 text-neutral-300 px-1.5 py-0.5 rounded text-[10px]">{o}</code>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400">S3 Public Endpoint</span>
              <span className={data.environment.s3_public_endpoint_set ? "text-emerald-400" : "text-amber-400"}>
                {data.environment.s3_public_endpoint_set ? "설정됨" : "미설정"}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400">Auth (Clerk)</span>
              <span className={data.environment.auth_enabled ? "text-emerald-400" : "text-neutral-500"}>
                {data.environment.auth_enabled ? "활성" : "비활성"}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400">Debug Mode</span>
              <span className={data.environment.debug ? "text-amber-400" : "text-neutral-500"}>
                {data.environment.debug ? "ON (개발)" : "OFF (프로덕션)"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Required env checklist */}
      {data && (
        <div>
          <p className="text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">필수 환경변수 체크리스트</p>
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
              {Object.entries(data.required_env).map(([key, ok]) => (
                <div key={key} className="flex items-center gap-2 text-xs">
                  <span className={ok ? "text-emerald-400" : "text-red-400"}>
                    {ok ? "✓" : "✗"}
                  </span>
                  <code className="text-neutral-400">{key}</code>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Release Verification */}
      <div>
        <p className="text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">릴리스 검수</p>
        <ReleaseChecklist mode="system" />
      </div>

      {/* Back link */}
      <div className="text-center pt-4">
        <a href="/" className="text-xs text-neutral-600 hover:text-neutral-400 transition">
          ← 홈으로
        </a>
      </div>
    </main>
  );
}
