"use client";

interface ImageVariantCardProps {
  assetId: string;
  url: string | null;
  status: string;
  isSelected: boolean;
  frameRole: string;
  qualityNote: string | null;
  promptPreview: string | null;
  onApprove: () => void;
  onReject: () => void;
  onSelect: () => void;
  disabled?: boolean;
}

const STATUS_STYLES: Record<string, { border: string; badge: string; badgeText: string }> = {
  approved: {
    border: "border-emerald-600/60 ring-1 ring-emerald-500/20",
    badge: "bg-emerald-600/20 text-emerald-400",
    badgeText: "승인됨",
  },
  rejected: {
    border: "border-red-800/40 opacity-50",
    badge: "bg-red-600/20 text-red-400",
    badgeText: "거부됨",
  },
  ready: {
    border: "border-amber-700/40",
    badge: "bg-amber-600/20 text-amber-400",
    badgeText: "검토 대기",
  },
  pending: {
    border: "border-neutral-800",
    badge: "bg-neutral-700/50 text-neutral-400",
    badgeText: "생성 중",
  },
};

const ROLE_COLORS: Record<string, string> = {
  start: "bg-emerald-900/60 text-emerald-300",
  middle: "bg-amber-900/60 text-amber-300",
  end: "bg-rose-900/60 text-rose-300",
};

export default function ImageVariantCard({
  assetId,
  url,
  status,
  isSelected,
  frameRole,
  qualityNote,
  promptPreview,
  onApprove,
  onReject,
  onSelect,
  disabled,
}: ImageVariantCardProps) {
  const styles = STATUS_STYLES[status] || STATUS_STYLES.ready;
  const isRejected = status === "rejected";
  const isApproved = status === "approved";

  return (
    <div className={`rounded-xl border overflow-hidden transition-all ${styles.border} ${
      isSelected ? "ring-2 ring-blue-500/40" : ""
    }`}>
      {/* Image */}
      <div className="relative aspect-[9/16] bg-neutral-900">
        {url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={url}
            alt={`Frame ${frameRole}`}
            className={`w-full h-full object-cover ${isRejected ? "grayscale opacity-40" : ""}`}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-neutral-600 text-xs">
            이미지 없음
          </div>
        )}

        {/* Badges overlay */}
        <div className="absolute top-2 left-2 flex flex-col gap-1">
          <span className={`rounded-md px-1.5 py-0.5 text-[9px] font-bold ${ROLE_COLORS[frameRole] || "bg-neutral-800 text-neutral-400"}`}>
            {frameRole.toUpperCase()}
          </span>
          <span className={`rounded-md px-1.5 py-0.5 text-[9px] font-bold ${styles.badge}`}>
            {styles.badgeText}
          </span>
        </div>

        {/* Selected badge */}
        {isSelected && (
          <div className="absolute top-2 right-2">
            <span className="rounded-md bg-blue-600 text-white px-1.5 py-0.5 text-[9px] font-bold">
              대표
            </span>
          </div>
        )}
      </div>

      {/* Prompt preview */}
      {promptPreview && (
        <div className="px-3 py-2 border-t border-neutral-800/50">
          <p className="text-[10px] text-neutral-500 line-clamp-3 leading-relaxed">
            {promptPreview}
          </p>
        </div>
      )}

      {/* Quality checklist (visual only, no scoring) */}
      {status === "ready" && url && (
        <div className="px-3 py-2 border-t border-neutral-800/50">
          <p className="text-[9px] text-neutral-600 font-medium mb-1">검토 항목</p>
          <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[9px] text-neutral-500">
            <span>☐ 인물 일관성</span>
            <span>☐ 구도 적합성</span>
            <span>☐ 배경 적합성</span>
            <span>☐ 스토리 연결</span>
          </div>
        </div>
      )}

      {/* Quality note */}
      {qualityNote && (
        <div className="px-3 py-1.5 border-t border-neutral-800/50">
          <p className="text-[9px] text-neutral-400 italic">{qualityNote}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="px-3 py-2 border-t border-neutral-800/50 flex gap-1.5">
        {!isApproved && !isRejected && (
          <>
            <button
              onClick={onApprove}
              disabled={disabled}
              className="flex-1 rounded-md bg-emerald-600/20 border border-emerald-700/40 py-1.5 text-[10px] font-medium text-emerald-400 hover:bg-emerald-600/30 transition disabled:opacity-50"
            >
              승인
            </button>
            <button
              onClick={onReject}
              disabled={disabled}
              className="flex-1 rounded-md bg-red-600/10 border border-red-800/30 py-1.5 text-[10px] font-medium text-red-400 hover:bg-red-600/20 transition disabled:opacity-50"
            >
              거부
            </button>
          </>
        )}

        {isApproved && !isSelected && (
          <button
            onClick={onSelect}
            disabled={disabled}
            className="flex-1 rounded-md bg-blue-600/20 border border-blue-700/40 py-1.5 text-[10px] font-medium text-blue-400 hover:bg-blue-600/30 transition disabled:opacity-50"
          >
            대표로 선택
          </button>
        )}

        {isApproved && isSelected && (
          <span className="flex-1 text-center py-1.5 text-[10px] text-emerald-400 font-medium">
            ✓ 승인 + 대표 이미지
          </span>
        )}

        {isRejected && (
          <button
            onClick={onApprove}
            disabled={disabled}
            className="flex-1 rounded-md bg-neutral-800 py-1.5 text-[10px] font-medium text-neutral-400 hover:text-neutral-200 transition disabled:opacity-50"
          >
            다시 승인
          </button>
        )}
      </div>
    </div>
  );
}
