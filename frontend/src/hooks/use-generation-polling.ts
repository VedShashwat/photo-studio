"use client";

import { useEffect, useRef } from "react";

import { ApiClientError, getGenerationJob } from "../lib/api-client";
import type { GenerationJobStatusResponse } from "../lib/types";

const DEFAULT_POLL_INTERVAL_MS = 1500;

export function useGenerationPolling(
  jobId: string | null,
  active: boolean,
  onUpdate: (status: GenerationJobStatusResponse) => void,
  onError: (message: string) => void,
  intervalMs = DEFAULT_POLL_INTERVAL_MS,
) {
  const onUpdateRef = useRef(onUpdate);
  const onErrorRef = useRef(onError);
  onUpdateRef.current = onUpdate;
  onErrorRef.current = onError;

  useEffect(() => {
    if (!jobId || !active) return;
    const activeJobId = jobId;
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    const controller = new AbortController();

    async function poll() {
      try {
        const status = await getGenerationJob(activeJobId, controller.signal);
        if (cancelled) return;
        onUpdateRef.current(status);
        if (status.status === "pending" || status.status === "running") {
          timeoutId = setTimeout(poll, intervalMs);
        }
      } catch (error) {
        if (cancelled || controller.signal.aborted) return;
        const message = error instanceof ApiClientError ? error.message : "Could not check generation status.";
        onErrorRef.current(message);
      }
    }

    void poll();
    return () => {
      cancelled = true;
      controller.abort();
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [active, intervalMs, jobId]);
}
