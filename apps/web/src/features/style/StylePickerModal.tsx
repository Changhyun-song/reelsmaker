"use client";

import { useState, useEffect } from "react";
import { apiUrl } from "@/lib/api";
import Modal from "@/components/ui/modal";
import Button from "@/components/ui/button";
import type { StylePreset } from "@/lib/types";
import { STYLE_CATEGORIES } from "@/lib/types";

interface StylePickerModalProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  activeStyleId: string | null;
  onSelect: (preset: StylePreset) => void;
}

export default function StylePickerModal({
  open,
  onClose,
  projectId,
  activeStyleId,
  onSelect,
}: StylePickerModalProps) {
  const [presets, setPresets] = useState<StylePreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetch(apiUrl(`/api/projects/${projectId}/styles`))
      .then((r) => r.json())
      .then((data) => {
        setPresets(Array.isArray(data) ? data : data.styles || []);
      })
      .catch(() => setPresets([]))
      .finally(() => setLoading(false));
  }, [open, projectId]);

  const filtered =
    filter === "all"
      ? presets
      : presets.filter(
          (p) =>
            p.rendering_style?.toLowerCase().includes(filter) ||
            p.name?.toLowerCase().includes(filter),
        );

  const handleSelect = async (preset: StylePreset) => {
    try {
      await fetch(
        apiUrl(`/api/projects/${projectId}/active-style/${preset.id}`),
        { method: "POST" },
      );
      onSelect(preset);
      onClose();
    } catch {
      /* silent */
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="스타일 프리셋 선택" maxWidth="max-w-4xl">
      {/* Category filter */}
      <div className="flex gap-2 overflow-x-auto pb-3 mb-4 scrollbar-hide">
        <button
          onClick={() => setFilter("all")}
          className={`shrink-0 rounded-full px-3.5 py-1.5 text-xs font-medium transition ${
            filter === "all"
              ? "bg-violet-600 text-white"
              : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
          }`}
        >
          전체
        </button>
        {STYLE_CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setFilter(cat.id)}
            className={`shrink-0 rounded-full px-3.5 py-1.5 text-xs font-medium transition ${
              filter === cat.id
                ? "bg-violet-600 text-white"
                : "bg-neutral-800 text-neutral-400 hover:text-neutral-200"
            }`}
          >
            {cat.name}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-3 max-h-[60vh] overflow-y-auto pr-1">
          {filtered.map((preset) => {
            const isActive = preset.id === activeStyleId;
            const isHovered = hoveredId === preset.id;

            return (
              <button
                key={preset.id}
                onClick={() => handleSelect(preset)}
                onMouseEnter={() => setHoveredId(preset.id)}
                onMouseLeave={() => setHoveredId(null)}
                className={`group relative rounded-xl border overflow-hidden transition-all ${
                  isActive
                    ? "border-violet-500 ring-2 ring-violet-500/30"
                    : "border-neutral-800 hover:border-neutral-600"
                }`}
              >
                {/* Preview image or gradient */}
                <div className="aspect-[4/3] bg-gradient-to-br from-neutral-800 to-neutral-900 relative overflow-hidden">
                  {preset.example_image_key ? (
                    <img
                      src={apiUrl(`/api/projects/${projectId}/assets/${preset.example_image_key}/url`)}
                      alt={preset.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-2xl opacity-30">
                        {preset.rendering_style === "anime"
                          ? "🎌"
                          : preset.rendering_style === "3d"
                            ? "🧊"
                            : preset.rendering_style === "cinematic"
                              ? "🎬"
                              : "🎨"}
                      </span>
                    </div>
                  )}

                  {/* Hover overlay */}
                  {(isHovered || isActive) && (
                    <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                      {isActive ? (
                        <span className="rounded-full bg-violet-600 px-3 py-1 text-[11px] font-bold text-white">
                          사용 중
                        </span>
                      ) : (
                        <span className="rounded-full bg-white/10 backdrop-blur-sm px-3 py-1 text-[11px] font-bold text-white">
                          선택
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Name */}
                <div className="p-2.5">
                  <p className="text-xs font-medium text-neutral-200 truncate">
                    {preset.name}
                  </p>
                  {preset.description && (
                    <p className="text-[10px] text-neutral-500 mt-0.5 truncate">
                      {preset.description}
                    </p>
                  )}
                </div>
              </button>
            );
          })}

          {filtered.length === 0 && (
            <div className="col-span-full py-12 text-center text-neutral-500 text-sm">
              스타일 프리셋이 없습니다.
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
