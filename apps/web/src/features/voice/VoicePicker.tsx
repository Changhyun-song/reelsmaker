"use client";

import { useState, useEffect, useRef } from "react";
import { apiUrl } from "@/lib/api";
import Modal from "@/components/ui/modal";
import Button from "@/components/ui/button";

interface VoiceInfo {
  id: string;
  name: string;
  language: string;
  preview_url?: string;
  labels?: Record<string, string>;
}

interface VoicePickerProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  selectedVoiceId: string | null;
  onSelect: (voice: VoiceInfo) => void;
}

export default function VoicePicker({
  open,
  onClose,
  projectId,
  selectedVoiceId,
  onSelect,
}: VoicePickerProps) {
  const [voices, setVoices] = useState<VoiceInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [playing, setPlaying] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetch(apiUrl(`/api/projects/${projectId}/voices`))
      .then((r) => r.json())
      .then((data) => setVoices(Array.isArray(data) ? data : []))
      .catch(() => setVoices([]))
      .finally(() => setLoading(false));
  }, [open, projectId]);

  const filtered = search
    ? voices.filter(
        (v) =>
          v.name.toLowerCase().includes(search.toLowerCase()) ||
          v.language?.toLowerCase().includes(search.toLowerCase()),
      )
    : voices;

  const handlePreview = (voice: VoiceInfo) => {
    if (playing === voice.id) {
      audioRef.current?.pause();
      setPlaying(null);
      return;
    }
    if (voice.preview_url) {
      if (audioRef.current) audioRef.current.pause();
      const audio = new Audio(voice.preview_url);
      audio.onended = () => setPlaying(null);
      audio.play();
      audioRef.current = audio;
      setPlaying(voice.id);
    }
  };

  const handleSelect = (voice: VoiceInfo) => {
    onSelect(voice);
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="보이스 선택" maxWidth="max-w-3xl">
      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="보이스 검색..."
          className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3.5 py-2.5 text-sm text-neutral-200 placeholder:text-neutral-500 focus:outline-none focus:border-violet-500 transition"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 max-h-[60vh] overflow-y-auto pr-1">
          {filtered.map((voice) => {
            const isSelected = voice.id === selectedVoiceId;

            return (
              <div
                key={voice.id}
                className={`rounded-xl border p-3.5 transition-all cursor-pointer ${
                  isSelected
                    ? "border-violet-500 bg-violet-950/20 ring-1 ring-violet-500/30"
                    : "border-neutral-800 bg-neutral-900/40 hover:border-neutral-600"
                }`}
                onClick={() => handleSelect(voice)}
              >
                <div className="flex items-center gap-3">
                  {/* Avatar */}
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-600 to-purple-700 flex items-center justify-center shrink-0">
                    <span className="text-sm font-bold text-white">
                      {voice.name.charAt(0).toUpperCase()}
                    </span>
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-neutral-200 truncate">
                      {voice.name}
                    </p>
                    <p className="text-[10px] text-neutral-500">
                      {voice.language || "Multi"}
                    </p>
                  </div>

                  {/* Preview button */}
                  {voice.preview_url && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePreview(voice);
                      }}
                      className={`w-8 h-8 rounded-full flex items-center justify-center transition ${
                        playing === voice.id
                          ? "bg-violet-600 text-white"
                          : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                      }`}
                    >
                      {playing === voice.id ? (
                        <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
                          <rect x="1" y="1" width="3" height="8" rx="0.5" />
                          <rect x="6" y="1" width="3" height="8" rx="0.5" />
                        </svg>
                      ) : (
                        <svg width="10" height="12" viewBox="0 0 10 12" fill="currentColor">
                          <path d="M0 0l10 6-10 6z" />
                        </svg>
                      )}
                    </button>
                  )}
                </div>

                {isSelected && (
                  <div className="mt-2 pt-2 border-t border-violet-700/30">
                    <span className="text-[10px] font-semibold text-violet-400">선택됨</span>
                  </div>
                )}
              </div>
            );
          })}

          {filtered.length === 0 && (
            <div className="col-span-full py-12 text-center text-neutral-500 text-sm">
              {search ? "검색 결과가 없습니다." : "사용 가능한 보이스가 없습니다."}
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
