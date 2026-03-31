"use client";

import { useState, useEffect, useCallback } from "react";
import { apiUrl } from "@/lib/api";
import StageResultCard, { type StageResult, type StageStatus } from "./StageResultCard";

/* ── Types ──────────────────────────────────────────── */

interface PipelineData {
  project_id: string;
  stages: Record<string, Record<string, unknown>>;
  warnings: string[];
  latest_by_type: Record<string, {
    status: string;
    error_message: string | null;
    created_at: string | null;
    completed_at: string | null;
  }>;
  providers: Record<string, string>;
}

interface DiagData {
  overall: string;
  connectivity: Record<string, { status: string; error?: string }>;
  providers: Record<string, { provider: string; mode: string; api_key_set: boolean | null }>;
  worker: { status: string; recent_completed?: number; stuck_queued?: number };
  error_count: number;
  warning_count: number;
}

interface ProjectSummary {
  id: string;
  title: string;
  status: string;
}

interface Props {
  projectId?: string;
  mode?: "project" | "system";
}

/* ── API helper ─────────────────────────────────────── */

async function api<T = unknown>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path));
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

/* ── Stage derivation from pipeline-inspect ─────────── */

function deriveStages(d: PipelineData): StageResult[] {
  const s = d.stages;
  const latest = d.latest_by_type;

  function jobInfo(type: string): { status: string; error: string | null; lastRun: string | null } {
    const j = latest[type];
    if (!j) return { status: "not_run", error: null, lastRun: null };
    return {
      status: j.status === "completed" ? "success" : j.status === "failed" ? "fail" : j.status,
      error: j.error_message || null,
      lastRun: j.completed_at || j.created_at || null,
    };
  }

  const results: StageResult[] = [];

  // 1. Script
  const scriptExists = (s.script as Record<string, unknown>)?.exists as boolean;
  const scriptJob = jobInfo("script_generate");
  results.push({
    key: "script",
    label: "대본 생성",
    status: scriptExists ? "success" : scriptJob.status === "fail" ? "fail" : "not_run",
    detail: scriptExists
      ? `버전 ${(s.script as Record<string, unknown>).version}, 상태: ${(s.script as Record<string, unknown>).status}`
      : "아직 대본이 생성되지 않았습니다",
    error: scriptJob.error,
    lastRun: (s.script as Record<string, unknown>)?.updated_at as string || scriptJob.lastRun,
    counts: null,
  });

  // 2. Scene
  const sceneCount = ((s.scene as Record<string, unknown>)?.count as number) || 0;
  const sceneJob = jobInfo("scene_generate");
  results.push({
    key: "scene",
    label: "씬 구성",
    status: sceneCount > 0 ? "success" : sceneJob.status === "fail" ? "fail" : "not_run",
    detail: sceneCount > 0 ? `${sceneCount}개 씬 생성됨` : "아직 씬이 구성되지 않았습니다",
    error: sceneJob.error,
    lastRun: sceneJob.lastRun,
    counts: sceneCount > 0 ? `${sceneCount}개` : null,
  });

  // 3. Shot/Frame
  const shotCount = ((s.shot as Record<string, unknown>)?.count as number) || 0;
  const frameCount = ((s.frame as Record<string, unknown>)?.count as number) || 0;
  const shotJob = jobInfo("shot_generate");
  const frameJob = jobInfo("frame_generate");
  const sfStatus: StageStatus = (shotCount > 0 && frameCount > 0)
    ? "success"
    : (shotCount > 0 && frameCount === 0)
      ? "partial"
      : shotJob.status === "fail" || frameJob.status === "fail"
        ? "fail"
        : "not_run";
  results.push({
    key: "shot_frame",
    label: "샷/프레임 구성",
    status: sfStatus,
    detail: shotCount > 0
      ? `${shotCount}개 샷, ${frameCount}개 프레임`
      : "아직 샷/프레임이 구성되지 않았습니다",
    error: frameJob.error || shotJob.error,
    lastRun: frameJob.lastRun || shotJob.lastRun,
    counts: shotCount > 0 ? `${shotCount}샷 / ${frameCount}프레임` : null,
  });

  // 4. Image
  const imgTotal = ((s.image as Record<string, unknown>)?.total as number) || 0;
  const imgReady = ((s.image as Record<string, unknown>)?.ready as number) || 0;
  const imgJob = jobInfo("image_generate");
  results.push({
    key: "image",
    label: "이미지 생성",
    status: imgReady > 0 ? "success" : imgTotal > 0 ? "partial" : imgJob.status === "fail" ? "fail" : "not_run",
    detail: imgTotal > 0
      ? `${imgTotal}개 생성, ${imgReady}개 준비됨`
      : "아직 이미지가 생성되지 않았습니다",
    error: imgJob.error,
    lastRun: imgJob.lastRun,
    counts: imgTotal > 0 ? `${imgReady}/${imgTotal}` : null,
  });

  // 5. Video
  const vidTotal = ((s.video as Record<string, unknown>)?.total as number) || 0;
  const vidReady = ((s.video as Record<string, unknown>)?.ready as number) || 0;
  const vidJob = jobInfo("video_generate");
  results.push({
    key: "video",
    label: "비디오 생성",
    status: vidReady > 0 ? "success" : vidTotal > 0 ? "partial" : vidJob.status === "fail" ? "fail" : "not_run",
    detail: vidTotal > 0
      ? `${vidTotal}개 생성, ${vidReady}개 준비됨`
      : "아직 비디오가 생성되지 않았습니다",
    error: vidJob.error,
    lastRun: vidJob.lastRun,
    counts: vidTotal > 0 ? `${vidReady}/${vidTotal}` : null,
  });

  // 6. TTS
  const ttsCount = ((s.tts as Record<string, unknown>)?.count as number) || 0;
  const ttsJob = jobInfo("tts_generate");
  results.push({
    key: "tts",
    label: "TTS 음성 생성",
    status: ttsCount > 0 ? "success" : ttsJob.status === "fail" ? "fail" : "not_run",
    detail: ttsCount > 0 ? `${ttsCount}개 음성 트랙 생성됨` : "아직 TTS가 실행되지 않았습니다",
    error: ttsJob.error,
    lastRun: ttsJob.lastRun,
    counts: ttsCount > 0 ? `${ttsCount}개` : null,
  });

  // 7. Render
  const renderTotal = ((s.render as Record<string, unknown>)?.total as number) || 0;
  const renderDone = ((s.render as Record<string, unknown>)?.completed as number) || 0;
  const renderJob = jobInfo("render_compose");
  results.push({
    key: "render",
    label: "최종 렌더 / MP4",
    status: renderDone > 0 ? "success" : renderTotal > 0 ? "partial" : renderJob.status === "fail" ? "fail" : "not_run",
    detail: renderTotal > 0
      ? `${renderTotal}개 렌더, ${renderDone}개 완료`
      : "아직 렌더링이 실행되지 않았습니다",
    error: renderJob.error,
    lastRun: renderJob.lastRun,
    counts: renderTotal > 0 ? `${renderDone}/${renderTotal}` : null,
  });

  return results;
}

/* ── Infra status card ──────────────────────────────── */

function InfraCard({ label, ok, detail, error }: { label: string; ok: boolean; detail: string; error?: string }) {
  return (
    <div className={`rounded-lg border p-3 ${ok ? "border-emerald-800/40 bg-emerald-950/10" : "border-red-800/40 bg-red-950/10"}`}>
      <div className="flex items-center justify-between mb-0.5">
        <span className="text-xs font-medium text-neutral-300">{label}</span>
        <span className={`text-[9px] font-bold ${ok ? "text-emerald-400" : "text-red-400"}`}>
          {ok ? "OK" : "FAIL"}
        </span>
      </div>
      <p className="text-[10px] text-neutral-500">{detail}</p>
      {error ? <p className="text-[9px] text-red-400/70 mt-0.5 line-clamp-1">{error}</p> : null}
    </div>
  );
}

/* ── Main component ─────────────────────────────────── */

export default function ReleaseChecklist({ projectId, mode = "project" }: Props) {
  const [pipeline, setPipeline] = useState<PipelineData | null>(null);
  const [diag, setDiag] = useState<DiagData | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set());
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const promises: Promise<unknown>[] = [];

      // Always fetch diagnostics
      promises.push(api<DiagData>("/api/diagnostics").then(setDiag).catch(() => null));

      // Fetch pipeline data for a specific project
      if (projectId) {
        promises.push(
          api<PipelineData>(`/api/projects/${projectId}/pipeline-inspect`).then(setPipeline).catch((e) => {
            setError(`파이프라인 데이터 로드 실패: ${e instanceof Error ? e.message : String(e)}`);
          })
        );
      }

      // For system mode, also get project list
      if (mode === "system") {
        promises.push(
          api<{ projects: ProjectSummary[] }>("/api/projects/").then((d) => setProjects(d.projects || [])).catch(() => null)
        );
      }

      await Promise.all(promises);
      setLastRefresh(new Date());
    } finally {
      setLoading(false);
    }
  }, [projectId, mode]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const toggle = (key: string) => {
    setCheckedItems((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const stages = pipeline ? deriveStages(pipeline) : [];
  const successCount = stages.filter(s => s.status === "success").length;
  const failCount = stages.filter(s => s.status === "fail").length;
  const checkedCount = stages.filter(s => checkedItems.has(s.key)).length;

  // Infra status from diagnostics
  const infraOk = diag
    ? {
        webApi: diag.connectivity?.postgres?.status === "ok",
        db: diag.connectivity?.postgres?.status === "ok",
        redis: diag.connectivity?.redis?.status === "ok",
        storage: diag.connectivity?.storage?.status === "ok",
        worker: diag.worker?.status === "active" || diag.worker?.status === "idle",
      }
    : null;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-bold text-neutral-200 flex items-center gap-2">
              릴리스 검수 체크리스트
              {stages.length > 0 ? (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-500 font-mono">
                  {successCount}/{stages.length} 성공 · {checkedCount}/{stages.length} 검수
                </span>
              ) : null}
            </h3>
            <p className="text-[10px] text-neutral-500 mt-0.5">
              현재 배포 버전에서 각 파이프라인 단계가 실제로 동작하는지 확인합니다.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {lastRefresh ? (
              <span className="text-[9px] text-neutral-600">
                {lastRefresh.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })} 기준
              </span>
            ) : null}
            <button
              onClick={fetchData}
              disabled={loading}
              className="rounded-md bg-neutral-800 border border-neutral-700/50 px-2.5 py-1 text-[10px] font-medium text-neutral-400 hover:text-neutral-200 transition disabled:opacity-40"
            >
              {loading ? "새로고침..." : "새로고침"}
            </button>
          </div>
        </div>

        {/* Summary progress bar */}
        {stages.length > 0 ? (
          <div className="flex items-center gap-3">
            <div className="flex-1 h-2 rounded-full bg-neutral-800 overflow-hidden">
              <div className="h-full flex">
                <div
                  className="bg-emerald-500 transition-all duration-500"
                  style={{ width: `${(successCount / stages.length) * 100}%` }}
                />
                <div
                  className="bg-red-500 transition-all duration-500"
                  style={{ width: `${(failCount / stages.length) * 100}%` }}
                />
              </div>
            </div>
            <div className="flex items-center gap-3 text-[9px] shrink-0">
              <span className="text-emerald-400">{successCount} 성공</span>
              {failCount > 0 ? <span className="text-red-400">{failCount} 실패</span> : null}
              <span className="text-neutral-600">
                {stages.length - successCount - failCount} 미실행
              </span>
            </div>
          </div>
        ) : null}
      </div>

      {/* Error */}
      {error ? (
        <div className="rounded-lg border border-red-800/50 bg-red-950/20 p-3">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      ) : null}

      {/* Infra status (from diagnostics) */}
      {infraOk ? (
        <div>
          <p className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider mb-2">인프라 상태</p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            <InfraCard
              label="Web ↔ API"
              ok={true}
              detail={diag?.overall === "healthy" ? "정상" : diag?.overall || "확인 중"}
            />
            <InfraCard
              label="Database"
              ok={infraOk.db}
              detail={infraOk.db ? "연결됨" : "연결 실패"}
              error={diag?.connectivity?.postgres?.error}
            />
            <InfraCard
              label="Redis"
              ok={infraOk.redis}
              detail={infraOk.redis ? "연결됨" : "연결 실패"}
              error={diag?.connectivity?.redis?.error}
            />
            <InfraCard
              label="Storage"
              ok={infraOk.storage}
              detail={infraOk.storage ? "접근 가능" : "접근 실패"}
              error={diag?.connectivity?.storage?.error}
            />
            <InfraCard
              label="Worker"
              ok={infraOk.worker}
              detail={
                diag?.worker?.status === "active"
                  ? `활성 (${diag.worker.recent_completed ?? 0}건 완료)`
                  : diag?.worker?.status === "idle"
                    ? "대기 중"
                    : diag?.worker?.status || "확인 불가"
              }
            />
          </div>
        </div>
      ) : null}

      {/* Provider status */}
      {diag?.providers ? (
        <div>
          <p className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider mb-2">AI Provider</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(diag.providers).map(([name, info]) => {
              const isMock = info.mode === "mock";
              const ok = isMock || info.api_key_set === true;
              return (
                <InfraCard
                  key={name}
                  label={name.charAt(0).toUpperCase() + name.slice(1)}
                  ok={ok}
                  detail={`${info.provider}${isMock ? " (테스트)" : ""}`}
                  error={!isMock && !info.api_key_set ? "API 키 미설정" : undefined}
                />
              );
            })}
          </div>
        </div>
      ) : null}

      {/* Pipeline stages */}
      {stages.length > 0 ? (
        <div>
          <p className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider mb-2">파이프라인 단계별 상태</p>
          <div className="space-y-2">
            {stages.map((stage) => (
              <StageResultCard
                key={stage.key}
                stage={stage}
                checked={checkedItems.has(stage.key)}
                onToggle={() => toggle(stage.key)}
              />
            ))}
          </div>
        </div>
      ) : (
        projectId && !loading ? (
          <div className="rounded-xl border border-neutral-800 bg-neutral-900/30 p-6 text-center">
            <p className="text-xs text-neutral-500">파이프라인 데이터를 불러올 수 없습니다.</p>
            <p className="text-[10px] text-neutral-600 mt-1">프로젝트 ID를 확인하세요.</p>
          </div>
        ) : null
      )}

      {/* Structural warnings from pipeline */}
      {pipeline && pipeline.warnings.length > 0 ? (
        <div className="rounded-xl border border-amber-800/30 bg-amber-950/10 p-4">
          <p className="text-[10px] font-bold text-amber-400 uppercase mb-2">구조 경고</p>
          <div className="space-y-1">
            {pipeline.warnings.map((w, i) => (
              <p key={i} className="text-[10px] text-amber-300/80 flex items-start gap-2">
                <span className="text-amber-400 shrink-0">▲</span> {w}
              </p>
            ))}
          </div>
        </div>
      ) : null}

      {/* Eval projects (system mode) */}
      {mode === "system" && projects.length > 0 ? (
        <div>
          <p className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider mb-2">
            평가용 프로젝트 ({projects.length}개)
          </p>
          <div className="space-y-1.5">
            {projects.slice(0, 10).map((p) => (
              <a
                key={p.id}
                href={`/projects/${p.id}`}
                className="flex items-center justify-between rounded-lg border border-neutral-800 bg-neutral-900/40 p-3 hover:border-neutral-700 transition"
              >
                <div>
                  <p className="text-xs font-medium text-neutral-300">{p.title}</p>
                  <p className="text-[9px] text-neutral-600 font-mono">{p.id.slice(0, 8)}...</p>
                </div>
                <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                  p.status === "completed" ? "bg-emerald-900/30 text-emerald-400"
                  : p.status === "draft" ? "bg-neutral-800 text-neutral-500"
                  : "bg-amber-900/30 text-amber-400"
                }`}>
                  {p.status}
                </span>
              </a>
            ))}
          </div>
        </div>
      ) : null}

      {/* Manual verification note */}
      <div className="rounded-lg border border-neutral-800/50 bg-neutral-900/20 p-3 text-center">
        <p className="text-[9px] text-neutral-600">
          체크박스는 로컬 UI 메모입니다 — 시스템 상태는 read-only이며 자동으로 판별됩니다.
        </p>
      </div>
    </div>
  );
}
