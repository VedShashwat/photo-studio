"use client";

import { useEffect, useState } from "react";

import { ApiClientError, apiUrl, getGenerationHistory } from "../../lib/api-client";
import type { GenerationHistoryItem, GenerationHistoryResponse } from "../../lib/types";

type HistoryPanelProps = {
  onRestore: (item: GenerationHistoryItem) => void;
  refreshKey?: string;
};

function formatDate(value: string | null): string {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleDateString();
}

function HistoryCard({ item, onRestore }: { item: GenerationHistoryItem; onRestore: () => void }) {
  const thumbnails = item.outputs.filter((output) => output.status === "succeeded" && output.thumbnail_url).slice(0, 3);
  return (
    <article className="history-card">
      <div className="history-card-heading">
        <div>
          <strong>{item.scene_preset?.replaceAll("_", " ") ?? "Custom scene"}</strong>
          <span>{formatDate(item.created_at)}</span>
        </div>
        <span className={`status-chip status-${item.status}`}>{item.status.replaceAll("_", " ")}</span>
      </div>
      <p className="history-prompt">{item.prompt ?? "Professional product photography"}</p>
      {thumbnails.length ? (
        <div className="history-thumbnails">
          {thumbnails.map((output) => (
            <img key={output.output_id} src={apiUrl(output.thumbnail_url as string)} alt={`Generated scene with seed ${output.seed ?? "unknown"}`} />
          ))}
        </div>
      ) : (
        <div className="history-empty-output">No completed outputs yet.</div>
      )}
      <div className="history-card-footer">
        <span>{item.outputs.length} output{item.outputs.length === 1 ? "" : "s"}</span>
        <button type="button" className="secondary-button" onClick={onRestore}>Restore job</button>
      </div>
    </article>
  );
}

export function HistoryPanel({ onRestore, refreshKey = "" }: HistoryPanelProps) {
  const [history, setHistory] = useState<GenerationHistoryResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getGenerationHistory(controller.signal)
      .then(setHistory)
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setErrorMessage(error instanceof ApiClientError ? error.message : "Could not load generation history.");
      });
    return () => controller.abort();
  }, [refreshKey]);

  return (
    <section className="history-panel" aria-labelledby="history-title" aria-busy={!history && !errorMessage}>
      <div className="section-heading">
        <div>
          <p className="eyebrow">WORKSPACE HISTORY</p>
          <h2 id="history-title">Return to a previous scene.</h2>
        </div>
        {history ? <span className="file-rule">{history.total} JOB{history.total === 1 ? "" : "S"}</span> : null}
      </div>
      {errorMessage ? <p className="error-message" role="alert">{errorMessage}</p> : null}
      {!history && !errorMessage ? (
        <div className="history-skeletons" role="status" aria-label="Loading recent generations">
          <span className="history-skeleton" />
          <span className="history-skeleton" />
        </div>
      ) : null}
      {history?.items.length === 0 ? <p className="history-loading">No generation history yet. Completed jobs will appear here.</p> : null}
      {history?.items.length ? (
        <div className="history-list">
          {history.items.map((item) => (
            <HistoryCard key={item.job_id} item={item} onRestore={() => onRestore(item)} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
