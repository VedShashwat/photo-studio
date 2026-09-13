"use client";

import { useEffect, useRef } from "react";

import { ApiClientError, getImage } from "../lib/api-client";
import type { ImageMetadataResponse } from "../lib/types";

const DEFAULT_POLL_INTERVAL_MS = 1000;

export function usePreprocessingPolling(
  imageId: string | null,
  active: boolean,
  onUpdate: (metadata: ImageMetadataResponse) => void,
  onError: (message: string) => void,
  intervalMs = DEFAULT_POLL_INTERVAL_MS,
) {
  const onUpdateRef = useRef(onUpdate);
  const onErrorRef = useRef(onError);
  onUpdateRef.current = onUpdate;
  onErrorRef.current = onError;

  useEffect(() => {
    if (!imageId || !active) return;
    const activeImageId = imageId;

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    const controller = new AbortController();

    async function poll() {
      try {
        const metadata = await getImage(activeImageId, controller.signal);
        if (cancelled) return;
        onUpdateRef.current(metadata);
        if (metadata.status === "processing" || metadata.status === "uploaded") {
          timeoutId = setTimeout(poll, intervalMs);
        }
      } catch (error) {
        if (cancelled || controller.signal.aborted) return;
        const message = error instanceof ApiClientError ? error.message : "Could not check preprocessing status.";
        onErrorRef.current(message);
      }
    }

    void poll();
    return () => {
      cancelled = true;
      controller.abort();
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [active, imageId, intervalMs]);
}
