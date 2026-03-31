"use client";

import { useState, useEffect, useCallback } from "react";
import { apiUrl } from "@/lib/api";

/* ── Types ──────────────────────────────────────────── */

interface StageScript {
  exists: boolean;
  status: string | null;
  version: number | null;
  updated_at: string | null;
}
interface StageCount { count: number; updated_at: string | null }
interface StageFrame extends StageCount {
  with_prompt: number;
  story_prompt_ratio: string;
}
interface StageAsset { total: number; ready: number }
interface StageRender { total: number; completed: number }

interface Stages {
  script: StageScript;
  scene: StageCount;
  shot: StageCount;
  frame: StageFrame;
  image: StageAsset;
  video: StageAsset;
  tts: StageCount;
  subtitle: StageCount;
  timeline: StageCount;
  render: StageRender;
}

interface JobInfo {
  id: string;
  job_type: string;
  status: string;
  progress: number;
  error_message: string | null;
  created_at: string | null;
  completed_at: string | null;
  result_preview: Record<string, unknown> | string | null;
  retry_count: number;
  max_retries: number;
}

interface ProviderRunInfo {
  provider: string;
  operation: string;
  model: string | null;
  status: string;
  latency_ms: number | null;
  error_message: string | null;
  created_at: string | null;
  cost_estimate: number | null;
}

interface PromptSample {
  frame_id: string;
  frame_role: string;
  visual_prompt_preview: string;
  has_negative: boolean;
}

interface PipelineData {
  project_id: string;
  stages: Stages;
  warnings: string[];
  recent_jobs: JobInfo[];
  latest_by_type: Record<string, JobInfo>;
  provider_runs: ProviderRunInfo[];
  prompt_samples: PromptSample[];
  providers: Record<string, string>;
}

/* ── Helpers ─────────────────────────────────────────── */

function relTime(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  const now = Date.now();
  const sec = Math.floor((now - d.getTime()) / 1000);
  if (sec < 60) return `${sec}초 전`;
  if (sec < 3600) return `${Math.floor(sec / 60)}분 전`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}시간 전`;
  return d.toLocaleDateString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-emerald-600/20 text-emerald-400 border-emerald-700/50",
  failed: "bg-red-600/20 text-red-400 border-red-700/50",
  running: "bg-blue-600/20 text-blue-400 border-blue-700/50",
  queued: "bg-amber-600/20 text-amber-400 border-amber-700/50",
};

function StatusDot({ status }: { status: string }) {
  const c = status === "completed" ? "bg-emerald-400"
    : status === "failed" ? "bg-red-400"
    : status === "running" ? "bg-blue-400 animate-pulse"
    : "bg-amber-400";
  return <span className={`inline-block w-2 h-2 rounded-full ${c}`} />;
}

function friendlyError(msg: string | null): string | null {
  if (!msg) return null;
  if (msg.includes("fetch") || msg.includes("ECONNREFUSED") || msg.includes("NetworkError"))
    return "API 연결 실패 — 서버가 실행 중인지 확인하세요";
  if (msg.includes("CORS") || msg.includes("cors"))
    return "CORS 오류 — API의 CORS_ORIGINS 설정을 확인하세요";
  if (msg.includes("401") || msg.includes("Authentication"))
    return "인증 오류 — AUTH_ENABLED 또는 API 키 설정을 확인하세요";
  if (msg.includes("timeout") || msg.includes("Timeout"))
    return "시간 초과 — provider 응답이 느립니다. 재시도하세요";
  if (msg.includes("mock") || msg.includes("Mock"))
    return "Mock provider 사용 중 — 실제 provider 설정이 필요합니다";
  if (msg.includes("Unknown job type"))
    return "Worker가 이 작업 유형을 인식하지 못합니다 — Worker를 재시작하세요";
  if (msg.length > 200) return msg.slice(0, 200) + "...";
  return msg;
}

/* ── Sub-components ──────────────────────────────────── */

function StageCard({
  name, label, status, count, extra, latestJob, icon,
}: {
  name: string;
  label: string;
  status: "ok" | "warn" | "error" | "empty" | "running";
  count: number | string;
  extra?: string;
  latestJob?: JobInfo | null;
  icon: string;
}) {
  const borderColor = status === "ok" ? "border-emerald-700/40"
    : status === "warn" ? "border-amber-700/40"
    : status === "error" ? "border-red-700/40"
    : status === "running" ? "border-blue-700/40"
    : "border-neutral-800";

  const bgColor = status === "ok" ? "bg-emerald-950/10"
    : status === "warn" ? "bg-amber-950/10"
    : status === "error" ? "bg-red-950/10"
    : status === "running" ? "bg-blue-950/10"
    : "bg-neutral-900/50";

  return (
    <div className={`rounded-lg border ${borderColor} ${bgColor} p-3`}>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-sm">{icon}</span>
          <span className="text-xs font-semibold text-neutral-300">{label}</span>
        </div>
        <span className={`text-sm font-bold ${
          status === "ok" ? "text-emerald-400"
          : status === "error" ? "text-red-400"
          : status === "warn" ? "text-amber-400"
          : status === "running" ? "text-blue-400"
          : "text-neutral-500"
        }`}>{count}</span>
      </div>

      {extra && <p className="text-[10px] text-neutral-500 mb-1">{extra}</p>}

      {latestJob && (
        <div className="flex items-center gap-1.5 mt-1">
          <StatusDot status={latestJob.status} />
          <span className="text-[10px] text-neutral-400">
            {latestJob.status === "running" ? `${latestJob.progress}%` : latestJob.status}
          </span>
          <span className="text-[10px] text-neutral-600">{relTime(latestJob.created_at)}</span>
        </div>
      )}

      {latestJob?.status === "failed" && latestJob.error_message && (
        <p className="text-[10px] text-red-400/80 mt-1 line-clamp-2">
          {friendlyError(latestJob.error_message)}
        </p>
      )}
    </div>
  );
}

function ProviderBadge({ name, value }: { name: string; value: string }) {
  const isMock = value === "mock" || value === "none";
  return (
    <div className={`flex items-center justify-between rounded-md px-2.5 py-1.5 text-xs ${
      isMock ? "bg-amber-950/30 border border-amber-800/40" : "bg-neutral-800/50 border border-neutral-700/30"
    }`}>
      <span className="text-neutral-400 font-medium">{name}</span>
      <span className={isMock ? "text-amber-400 font-bold" : "text-neutral-200"}>
        {value}
        {isMock && " (mock)"}
      </span>
    </div>
  );
}

function CollapsibleJson({ label, data }: { label: string; data: unknown }) {
  const [open, setOpen] = useState(false);
  if (!data) return null;
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="text-[10px] text-neutral-500 hover:text-neutral-300 transition flex items-center gap-1"
      >
        <span>{open ? "▾" : "▸"}</span>
        {label}
      </button>
      {open && (
        <pre className="mt-1 rounded-md bg-neutral-950 border border-neutral-800 p-2 text-[10px] text-neutral-400 overflow-x-auto max-h-40 overflow-y-auto">
          {typeof data === "string" ? data : JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

/* ── Main Component ─────────────────────────────────── */

export default function PipelineInspector({ projectId }: { projectId: string }) {
  const [data, setData] = useState<PipelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);
  const [showDebug, setShowDebug] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const r = await fetch(apiUrl(`/api/projects/${projectId}/pipeline-inspect`));
      if (!r.ok) {
        if (r.status === 401 || r.status === 403) {
          setError("인증 오류 — AUTH_ENABLED 설정을 확인하세요");
        } else if (r.status >= 500) {
          setError(`서버 오류 (${r.status}) — API 로그를 확인하세요`);
        } else {
          setError(`API 오류: ${r.status}`);
        }
        return;
      }
      const d = await r.json();
      setData(d);
      setError(null);
      setLastRefresh(new Date());
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("fetch") || msg.includes("Failed")) {
        setError("API 연결 실패 — NEXT_PUBLIC_API_URL 또는 서버 상태를 확인하세요");
      } else {
        setError(`연결 오류: ${msg}`);
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 5000);
    return () => clearInterval(id);
  }, [fetchData]);

  if (loading && !data) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-neutral-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-neutral-500">파이프라인 상태 로딩...</span>
        </div>
      </div>
    );
  }

  const stages = data?.stages;
  const latestByType = data?.latest_by_type ?? {};

  function getStageStatus(
    key: string,
    count: number,
    jobTypes: string[],
  ): "ok" | "warn" | "error" | "empty" | "running" {
    const latestJob = jobTypes.map(t => latestByType[t]).find(Boolean);
    if (latestJob?.status === "running" || latestJob?.status === "queued") return "running";
    if (latestJob?.status === "failed") return "error";
    if (count > 0) return "ok";
    return "empty";
  }

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-neutral-800/30 transition rounded-xl"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm">🔍</span>
          <span className="text-sm font-semibold text-neutral-200">Pipeline Inspector</span>
          {data && (
            <span className="text-[10px] text-neutral-600">
              {lastRefresh ? relTime(lastRefresh.toISOString()) + " 갱신" : ""}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {(data?.warnings?.length ?? 0) > 0 && (
            <span className="rounded-full bg-amber-600/20 text-amber-400 px-2 py-0.5 text-[10px] font-bold">
              {data!.warnings.length} 경고
            </span>
          )}
          {data?.recent_jobs?.some(j => j.status === "failed") && (
            <span className="rounded-full bg-red-600/20 text-red-400 px-2 py-0.5 text-[10px] font-bold">
              실패
            </span>
          )}
          <span className="text-neutral-500 text-xs">{expanded ? "▾" : "▸"}</span>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4">
          {/* Connection error */}
          {error && (
            <div className="rounded-lg border border-red-800/50 bg-red-950/20 p-3">
              <p className="text-xs font-bold text-red-400">연결 문제</p>
              <p className="text-xs text-red-300/80 mt-0.5">{error}</p>
            </div>
          )}

          {/* Warnings */}
          {data && data.warnings.length > 0 && (
            <div className="rounded-lg border border-amber-800/50 bg-amber-950/20 p-3 space-y-1">
              <p className="text-xs font-bold text-amber-400">구조 경고</p>
              {data.warnings.map((w, i) => (
                <p key={i} className="text-xs text-amber-300/80">• {w}</p>
              ))}
            </div>
          )}

          {/* Stage grid */}
          {stages && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
              <StageCard
                name="script" label="Script" icon="📝"
                status={stages.script.exists ? "ok" : "empty"}
                count={stages.script.exists ? `v${stages.script.version}` : "없음"}
                extra={stages.script.status || undefined}
                latestJob={latestByType["script_generate"] || latestByType["script_structure"]}
              />
              <StageCard
                name="scene" label="Scene" icon="🎬"
                status={getStageStatus("scene", stages.scene.count, ["scene_plan"])}
                count={stages.scene.count}
                latestJob={latestByType["scene_plan"]}
              />
              <StageCard
                name="shot" label="Shot" icon="🎯"
                status={getStageStatus("shot", stages.shot.count, ["shot_plan"])}
                count={stages.shot.count}
                latestJob={latestByType["shot_plan"]}
              />
              <StageCard
                name="frame" label="Frame" icon="🖼️"
                status={getStageStatus("frame", stages.frame.count, ["frame_plan"])}
                count={stages.frame.count}
                extra={`프롬프트: ${stages.frame.story_prompt_ratio}`}
                latestJob={latestByType["frame_plan"] || latestByType["story_prompts"]}
              />
              <StageCard
                name="image" label="Image" icon="🎨"
                status={getStageStatus("image", stages.image.ready, ["image_generate"])}
                count={`${stages.image.ready}/${stages.image.total}`}
                extra={stages.image.total > 0 ? `${stages.image.ready} ready` : undefined}
                latestJob={latestByType["image_generate"]}
              />
              <StageCard
                name="video" label="Video" icon="🎥"
                status={getStageStatus("video", stages.video.ready, ["video_generate"])}
                count={`${stages.video.ready}/${stages.video.total}`}
                latestJob={latestByType["video_generate"]}
              />
              <StageCard
                name="tts" label="TTS" icon="🔊"
                status={getStageStatus("tts", stages.tts.count, ["tts_generate"])}
                count={stages.tts.count}
                latestJob={latestByType["tts_generate"]}
              />
              <StageCard
                name="subtitle" label="Subtitle" icon="💬"
                status={getStageStatus("subtitle", stages.subtitle.count, ["subtitle_generate"])}
                count={stages.subtitle.count}
                latestJob={latestByType["subtitle_generate"]}
              />
              <StageCard
                name="timeline" label="Timeline" icon="⏱️"
                status={getStageStatus("timeline", stages.timeline.count, ["timeline_compose"])}
                count={stages.timeline.count}
                latestJob={latestByType["timeline_compose"]}
              />
              <StageCard
                name="render" label="Render" icon="🎞️"
                status={
                  stages.render.completed > 0 ? "ok"
                  : latestByType["render_final"]?.status === "failed" ? "error"
                  : latestByType["render_final"]?.status === "running" ? "running"
                  : "empty"
                }
                count={`${stages.render.completed}/${stages.render.total}`}
                latestJob={latestByType["render_final"]}
              />
            </div>
          )}

          {/* Providers */}
          {data?.providers && (
            <div>
              <p className="text-[10px] font-semibold text-neutral-500 mb-1.5 uppercase tracking-wider">
                Active Providers
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                {Object.entries(data.providers).map(([k, v]) => (
                  <ProviderBadge key={k} name={k} value={v} />
                ))}
              </div>
            </div>
          )}

          {/* Prompt samples */}
          {data?.prompt_samples && data.prompt_samples.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-neutral-500 mb-1.5 uppercase tracking-wider">
                Prompt Preview (처음 {data.prompt_samples.length}개 프레임)
              </p>
              <div className="space-y-1.5">
                {data.prompt_samples.map((ps) => (
                  <div key={ps.frame_id} className="rounded-md border border-neutral-800 bg-neutral-900/80 p-2">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
                        ps.frame_role === "start" ? "bg-emerald-900/60 text-emerald-300"
                        : ps.frame_role === "end" ? "bg-rose-900/60 text-rose-300"
                        : "bg-amber-900/60 text-amber-300"
                      }`}>{ps.frame_role}</span>
                      {ps.has_negative && (
                        <span className="text-[9px] text-neutral-500">+ negative prompt</span>
                      )}
                    </div>
                    <p className="text-[10px] text-neutral-400 leading-relaxed">
                      {ps.visual_prompt_preview || <span className="text-neutral-600 italic">프롬프트 없음</span>}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent errors */}
          {data?.recent_jobs?.some(j => j.status === "failed") && (
            <div>
              <p className="text-[10px] font-semibold text-red-400/80 mb-1.5 uppercase tracking-wider">
                Recent Errors
              </p>
              <div className="space-y-1.5">
                {data.recent_jobs
                  .filter(j => j.status === "failed")
                  .slice(0, 5)
                  .map((j) => (
                    <div key={j.id} className="rounded-md border border-red-900/40 bg-red-950/10 p-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <StatusDot status="failed" />
                          <span className="text-[10px] font-medium text-neutral-300">{j.job_type}</span>
                        </div>
                        <span className="text-[9px] text-neutral-600">{relTime(j.created_at)}</span>
                      </div>
                      <p className="text-[10px] text-red-400/80 mt-0.5">
                        {friendlyError(j.error_message)}
                      </p>
                      {j.retry_count > 0 && (
                        <p className="text-[9px] text-neutral-600 mt-0.5">
                          재시도: {j.retry_count}/{j.max_retries}
                        </p>
                      )}
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Debug toggle */}
          <div className="border-t border-neutral-800 pt-2">
            <button
              onClick={() => setShowDebug(!showDebug)}
              className="text-[10px] text-neutral-600 hover:text-neutral-400 transition"
            >
              {showDebug ? "▾ Debug 닫기" : "▸ Advanced Debug"}
            </button>
          </div>

          {showDebug && data && (
            <div className="space-y-2">
              {/* Recent provider runs */}
              {data.provider_runs.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold text-neutral-500 mb-1">
                    Provider Runs (최근 {data.provider_runs.length}개)
                  </p>
                  <div className="rounded-md border border-neutral-800 overflow-hidden">
                    <table className="w-full text-[10px]">
                      <thead>
                        <tr className="bg-neutral-800/50 text-neutral-500">
                          <th className="text-left px-2 py-1">Provider</th>
                          <th className="text-left px-2 py-1">Operation</th>
                          <th className="text-left px-2 py-1">Model</th>
                          <th className="text-left px-2 py-1">Status</th>
                          <th className="text-right px-2 py-1">Latency</th>
                          <th className="text-right px-2 py-1">Cost</th>
                          <th className="text-right px-2 py-1">Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.provider_runs.map((pr, i) => (
                          <tr key={i} className="border-t border-neutral-800/50">
                            <td className="px-2 py-1 text-neutral-300">{pr.provider}</td>
                            <td className="px-2 py-1 text-neutral-400">{pr.operation}</td>
                            <td className="px-2 py-1 text-neutral-500 max-w-24 truncate">{pr.model || "-"}</td>
                            <td className="px-2 py-1">
                              <span className={`inline-block rounded px-1 py-0.5 text-[9px] font-medium ${
                                STATUS_COLORS[pr.status] || "bg-neutral-800 text-neutral-400"
                              }`}>{pr.status}</span>
                            </td>
                            <td className="px-2 py-1 text-right text-neutral-500">
                              {pr.latency_ms ? `${(pr.latency_ms / 1000).toFixed(1)}s` : "-"}
                            </td>
                            <td className="px-2 py-1 text-right text-neutral-500">
                              {pr.cost_estimate ? `$${pr.cost_estimate.toFixed(4)}` : "-"}
                            </td>
                            <td className="px-2 py-1 text-right text-neutral-600">{relTime(pr.created_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* All recent jobs */}
              <div>
                <p className="text-[10px] font-semibold text-neutral-500 mb-1">
                  Recent Jobs (최근 {data.recent_jobs.length}개)
                </p>
                <div className="space-y-1">
                  {data.recent_jobs.map((j) => (
                    <div key={j.id} className="rounded-md border border-neutral-800 bg-neutral-950/50 p-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <StatusDot status={j.status} />
                          <span className="text-[10px] font-medium text-neutral-300">{j.job_type}</span>
                          {j.status === "running" && (
                            <span className="text-[9px] text-blue-400">{j.progress}%</span>
                          )}
                        </div>
                        <span className="text-[9px] text-neutral-600">{relTime(j.created_at)}</span>
                      </div>
                      {j.error_message && (
                        <p className="text-[10px] text-red-400/70 mt-0.5 line-clamp-2">
                          {friendlyError(j.error_message)}
                        </p>
                      )}
                      <CollapsibleJson label="Result JSON" data={j.result_preview} />
                    </div>
                  ))}
                </div>
              </div>

              {/* Raw JSON dump */}
              <CollapsibleJson label="Raw Pipeline Data (전체)" data={data} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
