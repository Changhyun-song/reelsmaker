export default function Home() {
  return (
    <main className="mx-auto max-w-5xl flex flex-col items-center justify-center gap-8 py-24">
      <h1 className="text-5xl font-bold tracking-tight">ReelsMaker</h1>
      <p className="max-w-md text-center text-lg text-neutral-400">
        주제 입력부터 최종 mp4 내보내기까지,
        <br />
        AI 기반 고품질 영상 제작 파이프라인.
      </p>
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
          className="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-medium transition hover:bg-neutral-700"
        >
          시스템 상태
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
