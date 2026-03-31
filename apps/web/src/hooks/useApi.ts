"use client";

import { useCallback } from "react";
import { apiUrl } from "@/lib/api";

export function useApi() {
  const apiFetch = useCallback(
    async <T = unknown>(path: string, opts?: RequestInit): Promise<T> => {
      const res = await fetch(apiUrl(path), {
        headers: { "Content-Type": "application/json" },
        ...opts,
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`API ${res.status}: ${text}`);
      }
      return res.json() as Promise<T>;
    },
    [],
  );

  return { apiFetch };
}
