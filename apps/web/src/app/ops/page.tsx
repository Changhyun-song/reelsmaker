"use client";

import { useEffect, useState, useCallback } from "react";

import { apiUrl } from "@/lib/api";

/* ── Types ──────────────────────────────────────────── */

interface RecentJob {
  id: string;
  job_type: string;
  status: string;
  progress: number;
  duration_sec: number | null;
  error_message: string | null;
  project_id: string | null;
  created_at: string;
}

interface ProviderStats {
  provider: string;
  total_runs: number;
  success: number;
  failed: number;
  success_rate: number;
  avg_latency_ms: number | null;
  p95_latency_ms: number | null;
  total_cost: number | null;
  total_input_tokens: number;
  total_output_tokens: number;
}

interface CategoryStats {
  operation: string;
  total_runs: number;
  success: number;
  failed: number;
  failure_rate: number;
  avg_latency_ms: number | null;
}

interface JobTypeStats {
  job_type: string;
  total: number;
  completed: number;
  failed: number;
  avg_duration_sec: number | null;
  failure_rate: number;
}

interface ProjectSummary {
  project_id: string;
  provider_runs: number;
  total_cost: number | null;
  total_latency_sec: number | null;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
}

interface OpsData {
  recent_jobs: RecentJob[];
  provider_stats: ProviderStats[];
  category_stats: CategoryStats[];
  job_type_stats: JobTypeStats[];
  project_summaries: ProjectSummary[];
  period_days: number;
}

/* ── Helpers ────────────────────────────────────────── */

const JOB_TYPE_LABELS: Record<string, string> = {
  demo: "데모",
  script_generate: "대본 생성",
  scene_plan: "씬 플랜",
  shot_plan: "샷 플랜",
  frame_plan: "프레임 플랜",
  image_generate: "이미지 생성",
  video_generate: "비디오 생성",
  tts_generate: "TTS 생성",
  subtitle_generate: "자막 생성",
  timeline_compose: "타임라인",
  render_final: "렌더",
};

const STATUS_COLORS: Record<string, string> = {
  queued: "text-yellow-400 bg-yellow-900/30",
  running: "text-blue-400 bg-blue-900/30",
  completed: "text-emerald-400 bg-emerald-900/30",
  failed: "text-red-400 bg-red-900/30",
  cancelled: "text-neutral-400 bg-neutral-800",
  success: "text-emerald-400 bg-emerald-900/30",
  started: "text-blue-400 bg-blue-900/30",
};

function Badge({ text, className }: { text: string; className?: string }) {
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold ${className ?? "bg-neutral-800 text-neutral-400"}`}
    >
      {text}
    </span>
  );
}

function fmtMs(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function fmtSec(sec: number | null): string {
  if (sec == null) return "—";
  if (sec < 60) return `${sec.toFixed(1)}s`;
  return `${Math.floor(sec / 60)}m ${Math.round(sec % 60)}s`;
}

function fmtCost(c: number | null): string {
  if (c == null || c === 0) return "—";
  if (c < 0.01) return `$${c.toFixed(5)}`;
  return `$${c.toFixed(3)}`;
}

function fmtTokens(n: number): string {
  if (n === 0) return "—";
  if (n < 1000) return `${n}`;
  return `${(n / 1000).toFixed(1)}k`;
}

function fmtTime(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtRate(rate: number): string {
  return `${rate.toFixed(1)}%`;
}

function RateBar({ rate, color }: { rate: number; color: string }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-neutral-800 overflow-hidden">
      <div
        className={`h-full rounded-full ${color} transition-all duration-500`}
        style={{ width: `${Math.min(rate, 100)}%` }}
      />
    </div>
  );
}

/* ── Component ──────────────────────────────────────── */

export default function OpsPage() {
  const [data, setData] = useState<OpsData | null>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/ops/stats?days=${days}`));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "연결 실패");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    setLoading(true);
    fetchData();
    const id = setInterval(fetchData, 15_000);
    return () => clearInterval(id);
  }, [fetchData]);

  return (
    <main className="mx-auto max-w-6xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">운영 모니터링</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Provider / Job / 프로젝트 수준 비용·시간·성공률 추적
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded bg-neutral-800 border border-neutral-700 px-3 py-1.5 text-sm text-neutral-200"
          >
            <option value={1}>최근 1일</option>
            <option value={3}>최근 3일</option>
            <option value={7}>최근 7일</option>
            <option value={14}>최근 14일</option>
            <option value={30}>최근 30일</option>
          </select>
          <button
            onClick={fetchData}
            disabled={loading}
            className="rounded bg-neutral-800 px-3 py-1.5 text-sm hover:bg-neutral-700 disabled:opacity-50 transition"
          >
            {loading ? "로딩..." : "새로고침"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded bg-red-900/30 border border-red-800/40 p-3 text-sm text-red-400">
          API 연결 오류: {error}
        </div>
      )}

      {data && (
        <div className="space-y-6">
          {/* Provider stats cards */}
          <Section title="Provider 통계">
            {data.provider_stats.length === 0 ? (
              <EmptyNote>Provider 실행 기록 없음</EmptyNote>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {data.provider_stats.map((p) => (
                  <div
                    key={p.provider}
                    className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-semibold text-sm text-neutral-200">
                        {p.provider}
                      </span>
                      <Badge
                        text={`${p.total_runs} runs`}
                        className="bg-neutral-800 text-neutral-300"
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-neutral-500">성공률</span>
                        <span
                          className={
                            p.success_rate >= 90
                              ? "text-emerald-400"
                              : p.success_rate >= 70
                                ? "text-yellow-400"
                                : "text-red-400"
                          }
                        >
                          {fmtRate(p.success_rate)}
                        </span>
                      </div>
                      <RateBar
                        rate={p.success_rate}
                        color={
                          p.success_rate >= 90
                            ? "bg-emerald-500"
                            : p.success_rate >= 70
                              ? "bg-yellow-500"
                              : "bg-red-500"
                        }
                      />
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] pt-1">
                        <Metric label="평균 latency" value={fmtMs(p.avg_latency_ms)} />
                        <Metric label="P95 latency" value={fmtMs(p.p95_latency_ms)} />
                        <Metric label="추정 비용" value={fmtCost(p.total_cost)} />
                        <Metric
                          label="실패"
                          value={`${p.failed}`}
                          valueClass={p.failed > 0 ? "text-red-400" : undefined}
                        />
                        <Metric label="Input tok" value={fmtTokens(p.total_input_tokens)} />
                        <Metric label="Output tok" value={fmtTokens(p.total_output_tokens)} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          {/* Category (operation) failure rates */}
          <Section title="카테고리별 실패율">
            {data.category_stats.length === 0 ? (
              <EmptyNote>카테고리 기록 없음</EmptyNote>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] text-neutral-500 border-b border-neutral-800">
                      <th className="pb-2 pr-4">Operation</th>
                      <th className="pb-2 pr-4 text-right">Total</th>
                      <th className="pb-2 pr-4 text-right">성공</th>
                      <th className="pb-2 pr-4 text-right">실패</th>
                      <th className="pb-2 pr-4 text-right">실패율</th>
                      <th className="pb-2 text-right">평균 Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.category_stats.map((c) => (
                      <tr
                        key={c.operation}
                        className="border-b border-neutral-800/50 hover:bg-neutral-800/30"
                      >
                        <td className="py-2 pr-4 font-medium text-neutral-300">
                          {c.operation}
                        </td>
                        <td className="py-2 pr-4 text-right text-neutral-400">
                          {c.total_runs}
                        </td>
                        <td className="py-2 pr-4 text-right text-emerald-400">
                          {c.success}
                        </td>
                        <td
                          className={`py-2 pr-4 text-right ${c.failed > 0 ? "text-red-400" : "text-neutral-500"}`}
                        >
                          {c.failed}
                        </td>
                        <td className="py-2 pr-4 text-right">
                          <span
                            className={
                              c.failure_rate > 20
                                ? "text-red-400"
                                : c.failure_rate > 5
                                  ? "text-yellow-400"
                                  : "text-neutral-400"
                            }
                          >
                            {fmtRate(c.failure_rate)}
                          </span>
                        </td>
                        <td className="py-2 text-right text-neutral-400">
                          {fmtMs(c.avg_latency_ms)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          {/* Job type performance */}
          <Section title="Job 유형별 성능">
            {data.job_type_stats.length === 0 ? (
              <EmptyNote>Job 기록 없음</EmptyNote>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] text-neutral-500 border-b border-neutral-800">
                      <th className="pb-2 pr-4">Job Type</th>
                      <th className="pb-2 pr-4 text-right">Total</th>
                      <th className="pb-2 pr-4 text-right">완료</th>
                      <th className="pb-2 pr-4 text-right">실패</th>
                      <th className="pb-2 pr-4 text-right">실패율</th>
                      <th className="pb-2 text-right">평균 소요</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.job_type_stats.map((j) => (
                      <tr
                        key={j.job_type}
                        className="border-b border-neutral-800/50 hover:bg-neutral-800/30"
                      >
                        <td className="py-2 pr-4 font-medium text-neutral-300">
                          {JOB_TYPE_LABELS[j.job_type] ?? j.job_type}
                        </td>
                        <td className="py-2 pr-4 text-right text-neutral-400">
                          {j.total}
                        </td>
                        <td className="py-2 pr-4 text-right text-emerald-400">
                          {j.completed}
                        </td>
                        <td
                          className={`py-2 pr-4 text-right ${j.failed > 0 ? "text-red-400" : "text-neutral-500"}`}
                        >
                          {j.failed}
                        </td>
                        <td className="py-2 pr-4 text-right">
                          <span
                            className={
                              j.failure_rate > 20
                                ? "text-red-400"
                                : j.failure_rate > 5
                                  ? "text-yellow-400"
                                  : "text-neutral-400"
                            }
                          >
                            {fmtRate(j.failure_rate)}
                          </span>
                        </td>
                        <td className="py-2 text-right text-neutral-400">
                          {fmtSec(j.avg_duration_sec)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          {/* Recent jobs */}
          <Section title="최근 Job (20개)">
            {data.recent_jobs.length === 0 ? (
              <EmptyNote>최근 작업 없음</EmptyNote>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] text-neutral-500 border-b border-neutral-800">
                      <th className="pb-2 pr-3">상태</th>
                      <th className="pb-2 pr-3">유형</th>
                      <th className="pb-2 pr-3 text-right">소요</th>
                      <th className="pb-2 pr-3">에러</th>
                      <th className="pb-2 text-right">시각</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_jobs.map((j) => (
                      <tr
                        key={j.id}
                        className="border-b border-neutral-800/50 hover:bg-neutral-800/30"
                      >
                        <td className="py-1.5 pr-3">
                          <Badge
                            text={j.status}
                            className={
                              STATUS_COLORS[j.status] ??
                              "bg-neutral-800 text-neutral-400"
                            }
                          />
                        </td>
                        <td className="py-1.5 pr-3 text-neutral-300">
                          {JOB_TYPE_LABELS[j.job_type] ?? j.job_type}
                        </td>
                        <td className="py-1.5 pr-3 text-right text-neutral-400">
                          {fmtSec(j.duration_sec)}
                        </td>
                        <td className="py-1.5 pr-3 max-w-[200px] truncate text-red-400/80 text-xs">
                          {j.error_message ?? ""}
                        </td>
                        <td className="py-1.5 text-right text-neutral-500 text-xs">
                          {fmtTime(j.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          {/* Project summaries */}
          <Section title="프로젝트별 요약">
            {data.project_summaries.length === 0 ? (
              <EmptyNote>프로젝트별 기록 없음</EmptyNote>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] text-neutral-500 border-b border-neutral-800">
                      <th className="pb-2 pr-4">Project ID</th>
                      <th className="pb-2 pr-4 text-right">Provider runs</th>
                      <th className="pb-2 pr-4 text-right">추정 비용</th>
                      <th className="pb-2 pr-4 text-right">총 latency</th>
                      <th className="pb-2 pr-4 text-right">Jobs</th>
                      <th className="pb-2 pr-4 text-right">완료</th>
                      <th className="pb-2 text-right">실패</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.project_summaries.map((p) => (
                      <tr
                        key={p.project_id}
                        className="border-b border-neutral-800/50 hover:bg-neutral-800/30"
                      >
                        <td className="py-1.5 pr-4">
                          <a
                            href={`/projects/${p.project_id}`}
                            className="font-mono text-xs text-blue-400 hover:underline"
                          >
                            {p.project_id.slice(0, 8)}…
                          </a>
                        </td>
                        <td className="py-1.5 pr-4 text-right text-neutral-300">
                          {p.provider_runs}
                        </td>
                        <td className="py-1.5 pr-4 text-right text-neutral-400">
                          {fmtCost(p.total_cost)}
                        </td>
                        <td className="py-1.5 pr-4 text-right text-neutral-400">
                          {fmtSec(p.total_latency_sec)}
                        </td>
                        <td className="py-1.5 pr-4 text-right text-neutral-300">
                          {p.total_jobs}
                        </td>
                        <td className="py-1.5 pr-4 text-right text-emerald-400">
                          {p.completed_jobs}
                        </td>
                        <td
                          className={`py-1.5 text-right ${p.failed_jobs > 0 ? "text-red-400" : "text-neutral-500"}`}
                        >
                          {p.failed_jobs}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>
        </div>
      )}

      {loading && !data && (
        <div className="flex items-center justify-center py-20 text-neutral-500">
          데이터 로딩 중...
        </div>
      )}
    </main>
  );
}

/* ── Sub-components ─────────────────────────────────── */

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="text-base font-semibold text-neutral-300 mb-3">{title}</h2>
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
        {children}
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div>
      <span className="text-neutral-500">{label}: </span>
      <span className={valueClass ?? "text-neutral-300"}>{value}</span>
    </div>
  );
}

function EmptyNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-sm text-neutral-600 text-center py-4">{children}</p>
  );
}
