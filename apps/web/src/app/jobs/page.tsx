"use client";

import { useEffect, useState, useCallback } from "react";
import { apiUrl } from "@/lib/api";

interface Job {
  id: string;
  project_id: string | null;
  job_type: string;
  status: string;
  progress: number;
  params: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  error_message: string | null;
  error_traceback: string | null;
  retry_count: number;
  max_retries: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

const STATUS_STYLES: Record<string, string> = {
  queued: "bg-yellow-900/50 text-yellow-400",
  running: "bg-blue-900/50 text-blue-400",
  completed: "bg-emerald-900/50 text-emerald-400",
  failed: "bg-red-900/50 text-red-400",
  cancelled: "bg-neutral-800 text-neutral-400",
};

const JOB_TYPE_LABELS: Record<string, string> = {
  demo: "데모",
  script_generate: "대본 생성",
  script_structure: "대본 구조화",
  image_generate: "이미지 생성",
  video_generate: "비디오 생성",
  tts_generate: "TTS 생성",
  subtitle_generate: "자막 생성",
  timeline_compose: "타임라인 합성",
  render_final: "최종 렌더",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_STYLES[status] ?? "bg-neutral-800 text-neutral-400"}`}
    >
      {status}
    </span>
  );
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-neutral-800">
      <div
        className="h-full rounded-full bg-blue-500 transition-all duration-500"
        style={{ width: `${Math.min(value, 100)}%` }}
      />
    </div>
  );
}

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function elapsed(start: string | null, end: string | null): string {
  if (!start) return "";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const sec = Math.round((e - s) / 1000);
  if (sec < 60) return `${sec}s`;
  return `${Math.floor(sec / 60)}m ${sec % 60}s`;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [enqueueing, setEnqueueing] = useState(false);

  const fetchJobs = useCallback(async () => {
    try {
      const res = await fetch(apiUrl("/api/jobs/?limit=50"));
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs);
        setTotal(data.total);
      }
    } catch {
      /* polling failure is silent */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    const id = setInterval(fetchJobs, 3000);
    return () => clearInterval(id);
  }, [fetchJobs]);

  const enqueueDemo = async (shouldFail: boolean = false) => {
    setEnqueueing(true);
    try {
      await fetch(apiUrl("/api/jobs/"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_type: "demo",
          params: { sleep_seconds: 5, should_fail: shouldFail },
          max_retries: shouldFail ? 2 : 0,
        }),
      });
      await fetchJobs();
    } finally {
      setEnqueueing(false);
    }
  };

  const retryJob = async (jobId: string) => {
    await fetch(apiUrl(`/api/jobs/${jobId}/retry`), { method: "POST" });
    await fetchJobs();
  };

  const cancelJob = async (jobId: string) => {
    await fetch(apiUrl(`/api/jobs/${jobId}/cancel`), { method: "POST" });
    await fetchJobs();
  };

  return (
    <main className="mx-auto max-w-5xl">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">작업 큐</h1>
          <p className="mt-1 text-sm text-neutral-500">
            총 {total}개 작업 · 3초마다 갱신
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => enqueueDemo(false)}
            disabled={enqueueing}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium transition hover:bg-blue-500 disabled:opacity-50"
          >
            데모 작업 (성공)
          </button>
          <button
            onClick={() => enqueueDemo(true)}
            disabled={enqueueing}
            className="rounded-lg bg-orange-700 px-4 py-2 text-sm font-medium transition hover:bg-orange-600 disabled:opacity-50"
          >
            데모 작업 (실패 + 재시도)
          </button>
        </div>
      </div>

      {loading && jobs.length === 0 && (
        <p className="text-neutral-500">불러오는 중...</p>
      )}

      <div className="space-y-3">
        {jobs.map((job) => {
          const isExpanded = expanded === job.id;
          return (
            <div
              key={job.id}
              className="rounded-xl border border-neutral-800 bg-neutral-900/50 overflow-hidden"
            >
              <button
                onClick={() => setExpanded(isExpanded ? null : job.id)}
                className="w-full px-5 py-4 text-left"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <StatusBadge status={job.status} />
                    <span className="font-medium truncate">
                      {JOB_TYPE_LABELS[job.job_type] ?? job.job_type}
                    </span>
                    {job.retry_count > 0 && (
                      <span className="text-xs text-neutral-500">
                        재시도 {job.retry_count}/{job.max_retries}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-neutral-500 shrink-0">
                    {job.status === "running" && (
                      <span className="text-blue-400 font-medium">
                        {job.progress}%
                      </span>
                    )}
                    <span>{formatTime(job.created_at)}</span>
                    {(job.status === "running" || job.status === "completed") && (
                      <span>{elapsed(job.started_at, job.completed_at)}</span>
                    )}
                    <span className="text-neutral-600">
                      {isExpanded ? "▲" : "▼"}
                    </span>
                  </div>
                </div>
                {job.status === "running" && (
                  <div className="mt-3">
                    <ProgressBar value={job.progress} />
                  </div>
                )}
              </button>

              {isExpanded && (
                <div className="border-t border-neutral-800 px-5 py-4 space-y-3 text-sm">
                  <div className="grid grid-cols-2 gap-2 text-neutral-400">
                    <div>
                      ID: <span className="text-neutral-300 font-mono text-xs">{job.id}</span>
                    </div>
                    <div>생성: {formatTime(job.created_at)}</div>
                    <div>시작: {formatTime(job.started_at)}</div>
                    <div>완료: {formatTime(job.completed_at)}</div>
                  </div>

                  {job.params && (
                    <div>
                      <p className="text-neutral-500 mb-1">파라미터</p>
                      <pre className="rounded bg-neutral-800 p-3 text-xs overflow-x-auto">
                        {JSON.stringify(job.params, null, 2)}
                      </pre>
                    </div>
                  )}

                  {job.result && (
                    <div>
                      <p className="text-emerald-500 mb-1">결과</p>
                      <pre className="rounded bg-neutral-800 p-3 text-xs overflow-x-auto">
                        {JSON.stringify(job.result, null, 2)}
                      </pre>
                    </div>
                  )}

                  {job.error_message && (
                    <div>
                      <p className="text-red-400 mb-1">에러</p>
                      <pre className="rounded bg-red-950/50 p-3 text-xs text-red-300 overflow-x-auto whitespace-pre-wrap">
                        {job.error_message}
                      </pre>
                    </div>
                  )}

                  {job.error_traceback && (
                    <details className="text-xs">
                      <summary className="cursor-pointer text-neutral-500 hover:text-neutral-300">
                        스택 트레이스
                      </summary>
                      <pre className="mt-1 rounded bg-neutral-800 p-3 overflow-x-auto whitespace-pre-wrap text-neutral-400">
                        {job.error_traceback}
                      </pre>
                    </details>
                  )}

                  <div className="flex gap-2 pt-1">
                    {(job.status === "failed" || job.status === "cancelled") && (
                      <button
                        onClick={() => retryJob(job.id)}
                        className="rounded bg-blue-700 px-3 py-1.5 text-xs font-medium hover:bg-blue-600"
                      >
                        재시도
                      </button>
                    )}
                    {job.status === "queued" && (
                      <button
                        onClick={() => cancelJob(job.id)}
                        className="rounded bg-neutral-700 px-3 py-1.5 text-xs font-medium hover:bg-neutral-600"
                      >
                        취소
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {!loading && jobs.length === 0 && (
        <div className="text-center py-16 text-neutral-500">
          <p className="text-lg mb-2">작업이 없습니다</p>
          <p className="text-sm">위 버튼으로 데모 작업을 추가해 보세요.</p>
        </div>
      )}
    </main>
  );
}
