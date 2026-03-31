"use client";

import { useState, useCallback } from "react";
import { apiUrl } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import Button from "@/components/ui/button";
import { LinearProgress, CircularProgress } from "@/components/ui/progress";
import type { Job } from "@/lib/types";

interface RenderPanelProps {
  projectId: string;
  timelineId: string | null;
  hasSubtitle: boolean;
}

type RenderStatus = "idle" | "rendering" | "complete" | "error";

export default function RenderPanel({ projectId, timelineId, hasSubtitle }: RenderPanelProps) {
  const { apiFetch } = useApi();
  const [status, setStatus] = useState<RenderStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [outputUrl, setOutputUrl] = useState<string | null>(null);
  const [srtUrl, setSrtUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [format, setFormat] = useState("mp4");
  const [quality, setQuality] = useState<"720p" | "1080p" | "4k">("1080p");
  const [elapsedSec, setElapsedSec] = useState(0);

  const startRender = useCallback(async () => {
    if (!timelineId) return;
    setStatus("rendering");
    setProgress(0);
    setError("");
    setOutputUrl(null);
    setSrtUrl(null);

    const startTime = Date.now();
    const timer = setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    try {
      const job = await apiFetch<Job>(`/api/projects/${projectId}/render`, {
        method: "POST",
        body: JSON.stringify({
          timeline_id: timelineId,
          format,
          include_subtitles: hasSubtitle,
        }),
      });

      // Poll
      while (true) {
        await new Promise((r) => setTimeout(r, 3000));
        const res = await fetch(apiUrl(`/api/jobs/${job.id}`));
        if (!res.ok) continue;
        const j: Job = await res.json();
        setProgress(j.progress);

        if (j.status === "completed") {
          // Fetch output
          try {
            const output = await apiFetch<{ url: string; srt_url?: string }>(
              `/api/projects/${projectId}/render-jobs/${job.id}/output`,
            );
            setOutputUrl(output.url || null);
            setSrtUrl(output.srt_url || null);
          } catch {
            /* video may be in result */
          }
          setStatus("complete");
          break;
        }
        if (j.status === "failed") {
          throw new Error(j.error_message || "렌더링 실패");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류");
      setStatus("error");
    } finally {
      clearInterval(timer);
    }
  }, [apiFetch, projectId, timelineId, format, hasSubtitle]);

  if (!timelineId) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-8 text-center">
        <p className="text-sm text-neutral-500">타임라인을 먼저 생성해주세요.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Settings */}
      {status === "idle" && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 space-y-4">
          <h3 className="text-sm font-bold text-neutral-200">렌더링 설정</h3>
          <div className="flex gap-4">
            {/* Quality */}
            <div className="flex-1">
              <label className="text-[11px] text-neutral-500 mb-1.5 block">화질</label>
              <div className="flex gap-2">
                {(["720p", "1080p", "4k"] as const).map((q) => (
                  <button
                    key={q}
                    onClick={() => setQuality(q)}
                    className={`flex-1 rounded-lg py-2 text-xs font-medium transition ${
                      quality === q
                        ? "bg-violet-600 text-white"
                        : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
                    }`}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <Button onClick={startRender} className="w-full" size="lg">
            렌더링 시작
          </Button>
        </div>
      )}

      {/* Rendering progress */}
      {status === "rendering" && (
        <div className="rounded-xl border border-violet-800/50 bg-violet-950/20 p-8 flex flex-col items-center gap-4">
          <CircularProgress value={progress} size={120} strokeWidth={8}>
            <div className="text-center">
              <span className="text-2xl font-bold text-neutral-100">{Math.round(progress)}</span>
              <span className="text-xs text-neutral-400">%</span>
            </div>
          </CircularProgress>
          <div className="text-center space-y-1">
            <p className="text-sm font-semibold text-neutral-200">렌더링 중...</p>
            <p className="text-xs text-neutral-500">{elapsedSec}초 경과</p>
          </div>
          <LinearProgress value={progress} className="max-w-xs" />
        </div>
      )}

      {/* Complete */}
      {status === "complete" && (
        <div className="rounded-xl border border-emerald-800/50 bg-emerald-950/20 p-6 space-y-4">
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-emerald-900/50 flex items-center justify-center">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-emerald-400">
                <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-emerald-400">렌더링 완료!</h3>
            <p className="text-xs text-neutral-400 mt-1">{elapsedSec}초 소요</p>
          </div>

          {/* Preview */}
          {outputUrl && (
            <div className="rounded-lg overflow-hidden bg-neutral-950 aspect-video">
              <video src={outputUrl} controls className="w-full h-full" />
            </div>
          )}

          {/* Download buttons */}
          <div className="flex gap-3">
            {outputUrl && (
              <a
                href={outputUrl}
                download
                className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white py-3 text-sm font-semibold transition"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M8 2v9M4 8l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M2 13h12" strokeLinecap="round" />
                </svg>
                MP4 다운로드
              </a>
            )}
            {srtUrl && (
              <a
                href={srtUrl}
                download
                className="flex items-center justify-center gap-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-200 px-5 py-3 text-sm font-semibold transition"
              >
                SRT 자막
              </a>
            )}
          </div>

          <Button variant="ghost" className="w-full" onClick={() => setStatus("idle")}>
            다시 렌더링
          </Button>
        </div>
      )}

      {/* Error */}
      {status === "error" && (
        <div className="rounded-xl border border-red-800/50 bg-red-950/20 p-5 text-center space-y-3">
          <p className="text-sm text-red-300">{error}</p>
          <Button variant="danger" size="sm" onClick={() => setStatus("idle")}>
            다시 시도
          </Button>
        </div>
      )}
    </div>
  );
}
