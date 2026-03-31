"use client";

import { useEffect, type ReactNode } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  maxWidth?: string;
  children: ReactNode;
}

export default function Modal({ open, onClose, title, maxWidth = "max-w-2xl", children }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        className={`${maxWidth} w-full mx-4 rounded-2xl border border-neutral-700/60 bg-neutral-900 shadow-2xl animate-in zoom-in-95 duration-200`}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <div className="flex items-center justify-between px-6 pt-5 pb-3">
            <h3 className="text-base font-bold text-neutral-100">{title}</h3>
            <button
              onClick={onClose}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-neutral-500 hover:bg-neutral-800 hover:text-neutral-200 transition"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
            </button>
          </div>
        )}
        <div className={title ? "px-6 pb-6" : "p-6"}>{children}</div>
      </div>
    </div>
  );
}
