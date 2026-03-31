"use client";

import { useState, useEffect, useCallback } from "react";
import { apiUrl } from "@/lib/api";
import Card from "@/components/ui/card";

interface CostLineItem {
  provider: string;
  operation: string;
  model: string | null;
  runs: number;
  total_cost: number;
  avg_cost: number;
  total_input_tokens: number;
  total_output_tokens: number;
  avg_latency_ms: number | null;
}

interface CostBreakdown {
  project_id: string;
  total_cost: number;
  line_items: CostLineItem[];
  by_category: Record<string, number>;
  summary: {
    total_cost_usd: number;
    total_runs: number;
    total_cost_krw: number;
  };
}

interface CostDashboardProps {
  projectId: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  "AI 플래닝": "bg-blue-500",
  "이미지 생성": "bg-emerald-500",
  "비디오 생성": "bg-violet-500",
  "음성 합성": "bg-amber-500",
  "자막": "bg-pink-500",
  "기타": "bg-neutral-500",
};

const CATEGORY_ICONS: Record<string, string> = {
  "AI 플래닝": "🧠",
  "이미지 생성": "🖼️",
  "비디오 생성": "🎬",
  "음성 합성": "🎤",
  "자막": "💬",
  "기타": "⚙️",
};

function formatUSD(v: number): string {
  if (v < 0.01) return `$${v.toFixed(4)}`;
  return `$${v.toFixed(2)}`;
}

function formatKRW(v: number): string {
  return `₩${Math.round(v).toLocaleString()}`;
}

export default function CostDashboard({ projectId }: CostDashboardProps) {
  const [data, setData] = useState<CostBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  const fetchCosts = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/ops/projects/${projectId}/costs`));
      if (res.ok) setData(await res.json());
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchCosts();
  }, [fetchCosts]);

  if (loading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-8">
          <div className="w-5 h-5 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </Card>
    );
  }

  if (!data || data.line_items.length === 0) {
    return (
      <Card>
        <div className="text-center py-6">
          <p className="text-sm text-neutral-500">아직 API 사용 내역이 없습니다.</p>
          <p className="text-xs text-neutral-600 mt-1">영상 생성을 시작하면 비용이 추적됩니다.</p>
        </div>
      </Card>
    );
  }

  const totalUSD = data.summary.total_cost_usd;
  const totalKRW = data.summary.total_cost_krw;
  const totalRuns = data.summary.total_runs;
  const categories = Object.entries(data.by_category).sort(([, a], [, b]) => b - a);
  const maxCategoryCost = categories.length > 0 ? categories[0][1] : 1;

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="text-center">
          <p className="text-[10px] text-neutral-500 font-medium mb-1">총 비용 (USD)</p>
          <p className="text-2xl font-bold text-violet-400">{formatUSD(totalUSD)}</p>
        </Card>
        <Card className="text-center">
          <p className="text-[10px] text-neutral-500 font-medium mb-1">총 비용 (KRW)</p>
          <p className="text-2xl font-bold text-emerald-400">{formatKRW(totalKRW)}</p>
        </Card>
        <Card className="text-center">
          <p className="text-[10px] text-neutral-500 font-medium mb-1">API 호출 수</p>
          <p className="text-2xl font-bold text-neutral-200">{totalRuns}</p>
        </Card>
      </div>

      {/* Category breakdown - visual bars */}
      <Card>
        <h3 className="text-sm font-bold text-neutral-200 mb-3">카테고리별 비용</h3>
        <div className="space-y-2.5">
          {categories.map(([cat, cost]) => {
            const pct = maxCategoryCost > 0 ? (cost / totalUSD) * 100 : 0;
            return (
              <div key={cat}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{CATEGORY_ICONS[cat] || "⚙️"}</span>
                    <span className="text-xs font-medium text-neutral-300">{cat}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-neutral-200">{formatUSD(cost)}</span>
                    <span className="text-[10px] text-neutral-500">{pct.toFixed(1)}%</span>
                  </div>
                </div>
                <div className="h-2 rounded-full bg-neutral-800">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${CATEGORY_COLORS[cat] || "bg-neutral-500"}`}
                    style={{ width: `${Math.max(pct, 1)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Pricing reference */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-neutral-200">수익구조 참고</h3>
          <span className="text-[10px] text-neutral-500">현재 프로젝트 기준</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-neutral-800/50 p-3">
            <p className="text-[10px] text-neutral-500 mb-1">1건 원가 (추정)</p>
            <p className="text-lg font-bold text-red-400">{formatUSD(totalUSD)}</p>
            <p className="text-[10px] text-neutral-600">{formatKRW(totalKRW)}</p>
          </div>
          <div className="rounded-lg bg-neutral-800/50 p-3">
            <p className="text-[10px] text-neutral-500 mb-1">마진 50% 판매가</p>
            <p className="text-lg font-bold text-emerald-400">{formatUSD(totalUSD * 2)}</p>
            <p className="text-[10px] text-neutral-600">{formatKRW(totalKRW * 2)}</p>
          </div>
        </div>
        <div className="mt-3 rounded-lg border border-amber-900/40 bg-amber-950/20 p-3">
          <p className="text-[10px] text-amber-400 font-medium mb-1">구독 모델 참고</p>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-xs font-bold text-neutral-200">Basic</p>
              <p className="text-[10px] text-neutral-500">10건/월</p>
              <p className="text-xs text-amber-400">{formatKRW(totalKRW * 10 * 2)}/월</p>
            </div>
            <div>
              <p className="text-xs font-bold text-neutral-200">Pro</p>
              <p className="text-[10px] text-neutral-500">50건/월</p>
              <p className="text-xs text-amber-400">{formatKRW(totalKRW * 50 * 1.5)}/월</p>
            </div>
            <div>
              <p className="text-xs font-bold text-neutral-200">Business</p>
              <p className="text-[10px] text-neutral-500">200건/월</p>
              <p className="text-xs text-amber-400">{formatKRW(totalKRW * 200 * 1.3)}/월</p>
            </div>
          </div>
        </div>
      </Card>

      {/* Detailed breakdown - expandable */}
      <Card>
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between text-left"
        >
          <h3 className="text-sm font-bold text-neutral-200">상세 호출 내역</h3>
          <span className="text-xs text-neutral-500">{expanded ? "▲ 접기" : "▼ 펼치기"}</span>
        </button>

        {expanded && (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-neutral-800">
                  <th className="text-left py-2 text-neutral-500 font-medium">Provider</th>
                  <th className="text-left py-2 text-neutral-500 font-medium">작업</th>
                  <th className="text-left py-2 text-neutral-500 font-medium">모델</th>
                  <th className="text-right py-2 text-neutral-500 font-medium">횟수</th>
                  <th className="text-right py-2 text-neutral-500 font-medium">총비용</th>
                  <th className="text-right py-2 text-neutral-500 font-medium">건당</th>
                  <th className="text-right py-2 text-neutral-500 font-medium">토큰</th>
                  <th className="text-right py-2 text-neutral-500 font-medium">지연(ms)</th>
                </tr>
              </thead>
              <tbody>
                {data.line_items.map((item, i) => (
                  <tr key={i} className="border-b border-neutral-800/50 hover:bg-neutral-800/30">
                    <td className="py-2 text-neutral-300 font-medium">{item.provider}</td>
                    <td className="py-2 text-neutral-400">{item.operation}</td>
                    <td className="py-2 text-neutral-500 max-w-[120px] truncate">{item.model || "—"}</td>
                    <td className="py-2 text-right text-neutral-300">{item.runs}</td>
                    <td className="py-2 text-right text-violet-400 font-medium">{formatUSD(item.total_cost)}</td>
                    <td className="py-2 text-right text-neutral-400">{formatUSD(item.avg_cost)}</td>
                    <td className="py-2 text-right text-neutral-500">
                      {item.total_input_tokens + item.total_output_tokens > 0
                        ? `${(item.total_input_tokens + item.total_output_tokens).toLocaleString()}`
                        : "—"}
                    </td>
                    <td className="py-2 text-right text-neutral-500">
                      {item.avg_latency_ms ? `${Math.round(item.avg_latency_ms)}` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-neutral-700">
                  <td colSpan={4} className="py-2 text-neutral-300 font-bold">합계</td>
                  <td className="py-2 text-right text-violet-400 font-bold">{formatUSD(totalUSD)}</td>
                  <td colSpan={3} />
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
