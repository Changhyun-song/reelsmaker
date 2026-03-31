"use client";

import { useState, useEffect, useCallback } from "react";
import { apiUrl } from "@/lib/api";
import ImageVariantCard from "./ImageVariantCard";

/* ── Types ──────────────────────────────────────────── */

interface FrameAsset {
  id: string;
  status: string;
  is_selected: boolean;
  url: string | null;
  metadata_: Record<string, unknown> | null;
  quality_note: string | null;
}

interface FrameGroup {
  frameId: string;
  frameRole: string;
  shotIndex: number;
  assets: FrameAsset[];
}

interface ApprovalSummary {
  total: number;
  approved: number;
  rejected: number;
  ready_for_review: number;
  pending: number;
  all_reviewed: boolean;
  approval_rate: number;
}

interface Shot {
  id: string;
  order_index: number;
  description?: string | null;
}

interface Frame {
  id: string;
  shot_id: string;
  frame_role: string;
  order_index: number;
  visual_prompt?: string | null;
}

interface Asset {
  id: string;
  parent_id: string;
  asset_type: string;
  status: string;
  is_selected: boolean;
  storage_key?: string;
  url?: string;
  metadata_?: Record<string, unknown>;
  quality_note?: string;
}

/* ── Main Component ──────────────────────────────────── */

interface ImageApprovalPanelProps {
  projectId: string;
  shots: Shot[];
  frames: Frame[];
  onApprovalChange?: () => void;
}

export default function ImageApprovalPanel({
  projectId,
  shots,
  frames,
  onApprovalChange,
}: ImageApprovalPanelProps) {
  const [frameGroups, setFrameGroups] = useState<FrameGroup[]>([]);
  const [summary, setSummary] = useState<ApprovalSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const api = useCallback(async (path: string, opts?: RequestInit) => {
    const res = await fetch(apiUrl(path), {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) throw new Error(`${res.status}: ${(await res.text()).slice(0, 200)}`);
    return res.json();
  }, []);

  const fetchAssets = useCallback(async () => {
    try {
      setError(null);
      const groups: FrameGroup[] = [];

      for (const frame of frames) {
        const shot = shots.find(s => s.id === frame.shot_id);
        const shotIdx = shot ? shot.order_index : 0;
        try {
          const res = await api(`/api/projects/${projectId}/frames/${frame.id}/assets`);
          const assets: Asset[] = res.assets || [];
          const imageAssets = assets.filter(a => a.asset_type === "image");

          if (imageAssets.length > 0) {
            groups.push({
              frameId: frame.id,
              frameRole: frame.frame_role || "start",
              shotIndex: shotIdx,
              assets: imageAssets.map(a => ({
                id: a.id,
                status: a.status,
                is_selected: a.is_selected,
                url: a.url || null,
                metadata_: a.metadata_ || null,
                quality_note: a.quality_note || null,
              })),
            });
          }
        } catch {
          // Skip frames with no assets
        }
      }

      setFrameGroups(groups);
    } catch (e) {
      setError(e instanceof Error ? e.message : "에셋 로딩 실패");
    } finally {
      setLoading(false);
    }
  }, [api, projectId, frames, shots]);

  const fetchSummary = useCallback(async () => {
    try {
      const data = await api(`/api/projects/${projectId}/approval-summary`);
      setSummary(data);
    } catch {
      // Non-critical
    }
  }, [api, projectId]);

  useEffect(() => {
    if (frames.length > 0) {
      fetchAssets();
      fetchSummary();
    } else {
      setLoading(false);
    }
  }, [fetchAssets, fetchSummary, frames.length]);

  const handleApprove = async (assetId: string) => {
    setActionLoading(assetId);
    try {
      await api(`/api/projects/${projectId}/assets/${assetId}/approve`, { method: "PATCH" });
      await fetchAssets();
      await fetchSummary();
      onApprovalChange?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "승인 실패");
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (assetId: string) => {
    setActionLoading(assetId);
    try {
      await api(`/api/projects/${projectId}/assets/${assetId}/reject`, { method: "PATCH" });
      await fetchAssets();
      await fetchSummary();
      onApprovalChange?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "거부 실패");
    } finally {
      setActionLoading(null);
    }
  };

  const handleSelect = async (assetId: string) => {
    setActionLoading(assetId);
    try {
      await api(`/api/projects/${projectId}/assets/${assetId}/select`, { method: "PATCH" });
      await fetchAssets();
      onApprovalChange?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "선택 실패");
    } finally {
      setActionLoading(null);
    }
  };

  const handleApproveAll = async () => {
    setActionLoading("bulk");
    try {
      for (const group of frameGroups) {
        for (const asset of group.assets) {
          if (asset.status === "ready") {
            await api(`/api/projects/${projectId}/assets/${asset.id}/approve`, { method: "PATCH" });
          }
        }
      }
      await fetchAssets();
      await fetchSummary();
      onApprovalChange?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "일괄 승인 실패");
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-6 text-center">
        <div className="w-5 h-5 border-2 border-neutral-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        <p className="text-xs text-neutral-500">이미지 에셋 로딩 중...</p>
      </div>
    );
  }

  if (frameGroups.length === 0) {
    return (
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-6 text-center">
        <p className="text-sm text-neutral-500">생성된 이미지가 없습니다.</p>
        <p className="text-xs text-neutral-600 mt-1">먼저 이미지 생성을 실행하세요.</p>
      </div>
    );
  }

  const readyCount = summary?.ready_for_review ?? 0;
  const approvedCount = summary?.approved ?? 0;
  const totalCount = summary?.total ?? 0;

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-bold text-neutral-200">이미지 승인</h3>
            <p className="text-xs text-neutral-500 mt-0.5">
              각 컷의 이미지를 검토하고 승인해 주세요. 승인된 이미지가 비디오 생성에 사용됩니다.
            </p>
          </div>
          {readyCount > 0 && (
            <button
              onClick={handleApproveAll}
              disabled={actionLoading === "bulk"}
              className="rounded-lg bg-emerald-600/20 border border-emerald-700/40 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:bg-emerald-600/30 transition disabled:opacity-50 shrink-0"
            >
              {actionLoading === "bulk" ? "처리 중..." : `전체 승인 (${readyCount}개)`}
            </button>
          )}
        </div>

        {/* Status counts */}
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span className="text-neutral-400">검토 대기 <span className="font-bold text-amber-400">{readyCount}</span></span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-neutral-400">승인 <span className="font-bold text-emerald-400">{approvedCount}</span></span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-400" />
            <span className="text-neutral-400">거부 <span className="font-bold text-red-400">{summary?.rejected ?? 0}</span></span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-neutral-600">총 {totalCount}개</span>
          </div>
        </div>

        {/* Progress bar */}
        {totalCount > 0 && (
          <div className="mt-2 h-1.5 rounded-full bg-neutral-800">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all duration-500"
              style={{ width: `${summary?.approval_rate ?? 0}%` }}
            />
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-800/50 bg-red-950/20 p-3 flex items-center justify-between">
          <p className="text-xs text-red-400">{error}</p>
          <button onClick={() => setError(null)} className="text-neutral-600 hover:text-neutral-400 text-xs">✕</button>
        </div>
      )}

      {/* Frame groups by shot */}
      {(() => {
        const shotMap = new Map<number, FrameGroup[]>();
        for (const group of frameGroups) {
          const list = shotMap.get(group.shotIndex) || [];
          list.push(group);
          shotMap.set(group.shotIndex, list);
        }

        return Array.from(shotMap.entries())
          .sort(([a], [b]) => a - b)
          .map(([shotIdx, groups]) => (
            <div key={shotIdx} className="space-y-2">
              <div className="flex items-center gap-2">
                <h4 className="text-xs font-bold text-neutral-400">Shot {shotIdx + 1}</h4>
                <span className="text-[9px] text-neutral-600">
                  {groups.reduce((n, g) => n + g.assets.length, 0)}개 이미지
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {groups.flatMap(group =>
                  group.assets.map(asset => (
                    <ImageVariantCard
                      key={asset.id}
                      assetId={asset.id}
                      url={asset.url}
                      status={asset.status}
                      isSelected={asset.is_selected}
                      frameRole={group.frameRole}
                      qualityNote={asset.quality_note}
                      promptPreview={
                        (asset.metadata_?.prompt_preview as string) || null
                      }
                      onApprove={() => handleApprove(asset.id)}
                      onReject={() => handleReject(asset.id)}
                      onSelect={() => handleSelect(asset.id)}
                      disabled={actionLoading === asset.id}
                    />
                  ))
                )}
              </div>
            </div>
          ));
      })()}

      {/* All reviewed message */}
      {summary?.all_reviewed && (
        <div className="rounded-xl border border-emerald-800/40 bg-emerald-950/10 p-4 text-center">
          <p className="text-sm font-medium text-emerald-400">모든 이미지를 검토했습니다</p>
          <p className="text-xs text-neutral-500 mt-0.5">
            승인된 이미지가 비디오 생성에 사용됩니다. 다음 단계로 진행하세요.
          </p>
        </div>
      )}
    </div>
  );
}
