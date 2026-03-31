"use client";

import type { ReactNode } from "react";

export type WorkspaceSection =
  | "overview"
  | "script"
  | "structure"
  | "style"
  | "storyboard"
  | "images"
  | "videos"
  | "tts-subtitle"
  | "timeline"
  | "render"
  | "qa"
  | "export";

export type StepStatus = "complete" | "in_progress" | "available" | "locked";

interface StepDef {
  key: WorkspaceSection;
  label: string;
  icon: string;
  group: string;
}

const WORKSPACE_STEPS: StepDef[] = [
  { key: "overview", label: "개요 · 다음 할 일", icon: "◆", group: "시작" },
  { key: "script", label: "① 대본 생성", icon: "✎", group: "기획 단계" },
  { key: "structure", label: "② 구조 분해", icon: "▦", group: "기획 단계" },
  { key: "style", label: "③ 스타일 설정", icon: "◈", group: "기획 단계" },
  { key: "storyboard", label: "④ 스토리보드", icon: "▤", group: "기획 단계" },
  { key: "images", label: "⑤ 이미지 생성", icon: "◻", group: "생성 단계" },
  { key: "videos", label: "⑥ 비디오 생성", icon: "▶", group: "생성 단계" },
  { key: "tts-subtitle", label: "⑦ TTS · 자막", icon: "♫", group: "생성 단계" },
  { key: "timeline", label: "⑧ 타임라인", icon: "≡", group: "합성 단계" },
  { key: "render", label: "⑨ 렌더", icon: "◎", group: "합성 단계" },
  { key: "qa", label: "⑩ 품질 검수", icon: "✓", group: "마무리" },
  { key: "export", label: "⑪ 내보내기", icon: "↗", group: "마무리" },
];

export { WORKSPACE_STEPS };

export default function WorkspaceLayout({
  projectTitle,
  projectDescription,
  section,
  onSectionChange,
  stepStatuses,
  sidebarFooter,
  children,
}: {
  projectTitle: string;
  projectDescription: string | null;
  section: WorkspaceSection;
  onSectionChange: (s: WorkspaceSection) => void;
  stepStatuses: Record<WorkspaceSection, StepStatus>;
  sidebarFooter?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-[calc(100vh-57px)]">
      <aside className="w-56 shrink-0 border-r border-neutral-800 bg-neutral-950/80 flex flex-col">
        <div className="px-4 py-3 border-b border-neutral-800">
          <a
            href="/projects"
            className="text-[11px] text-neutral-500 hover:text-neutral-300 transition"
          >
            ← 프로젝트 목록
          </a>
          <h2 className="text-sm font-bold text-neutral-200 mt-1.5 truncate">
            {projectTitle}
          </h2>
          {projectDescription && (
            <p className="text-[11px] text-neutral-500 mt-0.5 line-clamp-2">
              {projectDescription}
            </p>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto py-2 px-2">
          {WORKSPACE_STEPS.map((step, idx) => {
            const status = stepStatuses[step.key];
            const isActive = section === step.key;
            const isLocked = status === "locked";
            const showGroup =
              idx === 0 || step.group !== WORKSPACE_STEPS[idx - 1].group;

            return (
              <div key={step.key}>
                {showGroup && (
                  <p className="text-[9px] font-bold text-neutral-600 uppercase tracking-wider px-3 pt-3 pb-1">
                    {step.group}
                  </p>
                )}
                <button
                  onClick={() => !isLocked && onSectionChange(step.key)}
                  disabled={isLocked}
                  className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-left text-[13px] transition ${
                    isActive
                      ? "bg-blue-600/20 text-blue-300 font-medium"
                      : isLocked
                        ? "text-neutral-700 cursor-not-allowed"
                        : "text-neutral-400 hover:bg-neutral-800/80 hover:text-neutral-200"
                  }`}
                >
                  <span
                    className={`w-5 h-5 flex items-center justify-center rounded-full text-[10px] shrink-0 border ${
                      status === "complete"
                        ? "border-emerald-700 bg-emerald-900/40 text-emerald-400"
                        : status === "in_progress"
                          ? "border-blue-700 bg-blue-900/40 text-blue-400 animate-pulse"
                          : isLocked
                            ? "border-neutral-800 bg-neutral-900 text-neutral-700"
                            : isActive
                              ? "border-blue-600 bg-blue-900/30 text-blue-400"
                              : "border-neutral-700 bg-neutral-800/50 text-neutral-500"
                    }`}
                  >
                    {status === "complete" ? "✓" : step.icon}
                  </span>
                  <span className="truncate">{step.label}</span>
                </button>
              </div>
            );
          })}
        </nav>

        {sidebarFooter && (
          <div className="border-t border-neutral-800 p-3">{sidebarFooter}</div>
        )}
      </aside>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl px-8 py-6">{children}</div>
      </main>
    </div>
  );
}
