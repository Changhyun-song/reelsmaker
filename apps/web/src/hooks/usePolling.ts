"use client";

import { useEffect, useRef, useCallback } from "react";
import { apiUrl } from "@/lib/api";
import type { Job } from "@/lib/types";

export function useJobPolling(
  job: Job | null,
  onUpdate: (job: Job) => void,
  intervalMs = 2000,
) {
  const jobRef = useRef(job);
  jobRef.current = job;

  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") return;

    const id = setInterval(async () => {
      try {
        const res = await fetch(apiUrl(`/api/jobs/${jobRef.current!.id}`));
        if (res.ok) {
          const updated: Job = await res.json();
          onUpdate(updated);
        }
      } catch {
        /* silent */
      }
    }, intervalMs);

    return () => clearInterval(id);
  }, [job?.id, job?.status, onUpdate, intervalMs]);
}

export function usePollUntilDone() {
  const abortRef = useRef(false);

  const pollJob = useCallback(
    async (jobId: string, maxWaitSec = 600): Promise<Job> => {
      const start = Date.now();
      while (Date.now() - start < maxWaitSec * 1000) {
        if (abortRef.current) throw new Error("중단됨");
        await new Promise((r) => setTimeout(r, 2500));
        const res = await fetch(apiUrl(`/api/jobs/${jobId}`));
        if (!res.ok) continue;
        const job: Job = await res.json();
        if (job.status === "completed") return job;
        if (job.status === "failed")
          throw new Error(job.error_message || "작업 실패");
      }
      throw new Error("시간 초과");
    },
    [],
  );

  const abort = useCallback(() => {
    abortRef.current = true;
  }, []);

  const reset = useCallback(() => {
    abortRef.current = false;
  }, []);

  return { pollJob, abort, reset };
}
