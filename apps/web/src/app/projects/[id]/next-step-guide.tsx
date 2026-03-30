"use client";

import type { WorkspaceSection, StepStatus } from "./workspace-layout";

interface GuideStep {
  section: WorkspaceSection;
  number: number;
  title: string;
  description: string;
  action: string;
}

const PIPELINE_STEPS: GuideStep[] = [
  {
    section: "script",
    number: 1,
    title: "대본 생성",
    description: "영상의 주제, 타깃, 톤, 길이를 입력하면 AI가 구조화된 대본을 생성합니다.",
    action: "대본 생성하러 가기",
  },
  {
    section: "structure",
    number: 2,
    title: "Scene/Shot/Frame 분해",
    description: "대본을 장면(Scene) → 샷(Shot) → 프레임(Frame)으로 세분화합니다.",
    action: "구조 분해하러 가기",
  },
  {
    section: "style",
    number: 3,
    title: "스타일 & 캐릭터 설정",
    description: "영상 톤, 색감, 카메라 스타일, 등장 캐릭터를 설정합니다.",
    action: "스타일 설정하러 가기",
  },
  {
    section: "images",
    number: 4,
    title: "이미지 생성",
    description: "각 프레임의 시작/끝 이미지를 AI로 생성합니다.",
    action: "이미지 생성하러 가기",
  },
  {
    section: "videos",
    number: 5,
    title: "비디오 클립 생성",
    description: "각 샷을 2~8초짜리 비디오 클립으로 생성합니다.",
    action: "비디오 생성하러 가기",
  },
  {
    section: "tts-subtitle",
    number: 6,
    title: "TTS & 자막",
    description: "나레이션 음성을 생성하고 자막(SRT)을 만듭니다.",
    action: "TTS/자막 생성하러 가기",
  },
  {
    section: "timeline",
    number: 7,
    title: "타임라인 합성",
    description: "모든 클립, 음성, 자막을 하나의 타임라인으로 조립합니다.",
    action: "타임라인 합성하러 가기",
  },
  {
    section: "render",
    number: 8,
    title: "최종 렌더",
    description: "타임라인을 MP4 영상으로 렌더링합니다.",
    action: "렌더하러 가기",
  },
  {
    section: "qa",
    number: 9,
    title: "품질 검수",
    description: "누락된 자산, 시간 불일치 등을 자동 점검합니다.",
    action: "QA 실행하러 가기",
  },
  {
    section: "export",
    number: 10,
    title: "내보내기",
    description: "MP4, SRT, 프로젝트 JSON을 다운로드합니다.",
    action: "내보내기로 가기",
  },
];

export default function NextStepGuide({
  currentSection,
  stepStatuses,
  onNavigate,
  hasApiKey,
}: {
  currentSection: WorkspaceSection;
  stepStatuses: Record<WorkspaceSection, StepStatus>;
  onNavigate: (s: WorkspaceSection) => void;
  hasApiKey: boolean;
}) {
  if (currentSection !== "overview") return null;

  const nextStep = PIPELINE_STEPS.find(
    (s) =>
      stepStatuses[s.section] === "available" ||
      stepStatuses[s.section] === "in_progress"
  );

  const completedCount = PIPELINE_STEPS.filter(
    (s) => stepStatuses[s.section] === "complete"
  ).length;

  const progressPct = Math.round((completedCount / PIPELINE_STEPS.length) * 100);

  return (
    <div className="space-y-4">
      {/* API key warning */}
      {!hasApiKey && (
        <div className="rounded-lg border border-amber-700/50 bg-amber-950/30 px-4 py-3">
          <p className="text-sm font-semibold text-amber-400">
            AI 기능을 사용하려면 API 키가 필요합니다
          </p>
          <p className="text-xs text-amber-400/70 mt-1">
            <code className="bg-amber-900/40 px-1 rounded">.env.local</code> 파일에{" "}
            <code className="bg-amber-900/40 px-1 rounded">ANTHROPIC_API_KEY=sk-ant-...</code>를
            설정한 뒤 컨테이너를 재시작하세요. 없으면 Mock 모드로 이미지/비디오만 테스트 가능합니다.
          </p>
        </div>
      )}

      {/* Progress bar */}
      <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-neutral-300">
            전체 진행률
          </span>
          <span className="text-sm text-neutral-500">
            {completedCount}/{PIPELINE_STEPS.length} 단계 완료
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-neutral-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-blue-500 transition-all duration-700"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Next step highlight */}
      {nextStep && (
        <div className="rounded-lg border-2 border-blue-600/60 bg-blue-950/20 p-5">
          <div className="flex items-start gap-4">
            <div className="shrink-0 w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-lg font-bold">
              {nextStep.number}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-base font-bold text-blue-300">
                다음 단계: {nextStep.title}
              </p>
              <p className="text-sm text-neutral-400 mt-1">
                {nextStep.description}
              </p>
              <button
                onClick={() => onNavigate(nextStep.section)}
                className="mt-3 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 transition"
              >
                {nextStep.action} →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Full pipeline overview */}
      <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-4">
        <h3 className="text-sm font-semibold text-neutral-300 mb-3">
          영상 제작 파이프라인
        </h3>
        <div className="space-y-1">
          {PIPELINE_STEPS.map((step) => {
            const status = stepStatuses[step.section];
            const isNext = nextStep?.section === step.section;
            return (
              <button
                key={step.section}
                onClick={() =>
                  status !== "locked" && onNavigate(step.section)
                }
                disabled={status === "locked"}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition ${
                  isNext
                    ? "bg-blue-900/20 border border-blue-700/40"
                    : status === "locked"
                      ? "opacity-40 cursor-not-allowed"
                      : "hover:bg-neutral-800/60"
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                    status === "complete"
                      ? "bg-emerald-600 text-white"
                      : status === "in_progress"
                        ? "bg-blue-600 text-white animate-pulse"
                        : isNext
                          ? "bg-blue-600/30 text-blue-300 border border-blue-500"
                          : "bg-neutral-800 text-neutral-500"
                  }`}
                >
                  {status === "complete" ? "✓" : step.number}
                </div>
                <div className="flex-1 min-w-0">
                  <span
                    className={`text-sm ${
                      status === "complete"
                        ? "text-emerald-400"
                        : isNext
                          ? "text-blue-300 font-medium"
                          : status === "locked"
                            ? "text-neutral-600"
                            : "text-neutral-400"
                    }`}
                  >
                    {step.title}
                  </span>
                </div>
                <span
                  className={`text-[10px] shrink-0 ${
                    status === "complete"
                      ? "text-emerald-500"
                      : status === "in_progress"
                        ? "text-blue-400"
                        : status === "locked"
                          ? "text-neutral-700"
                          : "text-neutral-600"
                  }`}
                >
                  {status === "complete"
                    ? "완료"
                    : status === "in_progress"
                      ? "진행 중..."
                      : status === "locked"
                        ? "이전 단계 필요"
                        : "대기"}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
