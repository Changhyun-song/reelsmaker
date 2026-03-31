"use client";

import { useEffect, useState } from "react";
import { apiUrl } from "@/lib/api";

interface DiagSummary {
  overall: string;
  error_count: number;
  warning_count: number;
}

function EnvBanner({ diag }: { diag: DiagSummary | null; }) {
  if (!diag) return null;
  if (diag.overall === "healthy") return null;

  const isError = diag.overall === "unhealthy";
  return (
    <a
      href="/status"
      className={`w-full max-w-2xl rounded-lg border px-4 py-3 flex items-center justify-between transition hover:opacity-90 ${
        isError
          ? "border-red-800/50 bg-red-950/20"
          : "border-amber-800/50 bg-amber-950/20"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className={isError ? "text-red-400" : "text-amber-400"}>
          {isError ? "✖" : "▲"}
        </span>
        <div>
          <p className={`text-sm font-medium ${isError ? "text-red-300" : "text-amber-300"}`}>
            {isError ? "시스템 문제 발견" : "환경 설정 경고"}
          </p>
          <p className="text-xs text-neutral-500">
            에러 {diag.error_count}건, 경고 {diag.warning_count}건
          </p>
        </div>
      </div>
      <span className="text-xs text-neutral-500">진단 페이지 →</span>
    </a>
  );
}

function ApiConnBanner({ ok }: { ok: boolean | null }) {
  if (ok !== false) return null;
  const apiUrlValue = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return (
    <a
      href="/status"
      className="w-full max-w-2xl rounded-lg border border-red-800/50 bg-red-950/20 px-4 py-3 flex items-center justify-between transition hover:opacity-90"
    >
      <div className="flex items-center gap-2">
        <span className="text-red-400">✖</span>
        <div>
          <p className="text-sm font-medium text-red-300">API 연결 실패</p>
          <p className="text-xs text-neutral-500">{apiUrlValue}에 연결할 수 없습니다</p>
        </div>
      </div>
      <span className="text-xs text-neutral-500">진단 페이지 →</span>
    </a>
  );
}

export default function Home() {
  const [diag, setDiag] = useState<DiagSummary | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);

  useEffect(() => {
    fetch(apiUrl("/api/diagnostics"))
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(d => { setDiag(d); setApiOk(true); })
      .catch(() => setApiOk(false));
  }, []);

  return (
    <main className="mx-auto max-w-5xl flex flex-col items-center justify-center gap-8 py-24">
      <h1 className="text-5xl font-bold tracking-tight">ReelsMaker</h1>
      <p className="max-w-md text-center text-lg text-neutral-400">
        주제 입력부터 최종 mp4 내보내기까지,
        <br />
        AI 기반 고품질 영상 제작 파이프라인.
      </p>

      <ApiConnBanner ok={apiOk} />
      <EnvBanner diag={diag} />

      <div className="flex gap-3 pt-4">
        <a
          href="/projects"
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium transition hover:bg-blue-500"
        >
          프로젝트
        </a>
        <a
          href="/jobs"
          className="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-medium transition hover:bg-neutral-700"
        >
          작업 큐
        </a>
        <a
          href="/ops"
          className="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-medium transition hover:bg-neutral-700"
        >
          운영 모니터링
        </a>
        <a
          href="/status"
          className={`rounded-lg px-5 py-2.5 text-sm font-medium transition ${
            diag && diag.overall !== "healthy"
              ? "bg-amber-800/30 border border-amber-700/50 text-amber-300 hover:bg-amber-800/50"
              : "bg-neutral-800 hover:bg-neutral-700"
          }`}
        >
          시스템 진단
          {diag && diag.overall !== "healthy" && (
            <span className="ml-1.5 rounded-full bg-amber-600/30 text-amber-400 px-1.5 py-0.5 text-[10px] font-bold">
              {diag.error_count + diag.warning_count}
            </span>
          )}
        </a>
        <a
          href={`${process.env.NEXT_PUBLIC_API_DOCS || "http://localhost:8000"}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg border border-neutral-700 px-5 py-2.5 text-sm font-medium transition hover:bg-neutral-900"
        >
          API 문서
        </a>
      </div>
    </main>
  );
}
