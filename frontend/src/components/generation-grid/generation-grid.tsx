"use client";

import { apiUrl } from "../../lib/api-client";
import type { GenerationJobStatusResponse, GenerationOutput } from "../../lib/types";

type GenerationGridProps = {
  status: GenerationJobStatusResponse;
  selectedOutputId: string | null;
  onSelectOutput: (outputId: string) => void;
};

function OutputCard({ output, selected, onSelect }: { output: GenerationOutput; selected: boolean; onSelect: () => void }) {
  const isReady = output.status === "succeeded";
  return (
    <article className={`output-card${selected ? " is-selected" : ""}`}>
      <button type="button" className="output-select" onClick={onSelect} aria-pressed={selected} disabled={!isReady}>
        {isReady ? (
          <img src={apiUrl(output.url)} alt={`Generated variation with seed ${output.seed ?? "unknown"}`} />
        ) : (
          <span className="output-placeholder" role="status">{output.status}</span>
        )}
      </button>
      <div className="output-meta">
        <span>Seed {output.seed ?? "—"}</span>
        <span>{output.status}</span>
      </div>
      {isReady ? (
        <a className="output-download" href={apiUrl(output.download_url)} download>
          Download
        </a>
      ) : null}
    </article>
  );
}

export function GenerationGrid({ status, selectedOutputId, onSelectOutput }: GenerationGridProps) {
  if (!status.outputs.length) return null;
  const firstReadyOutput = status.outputs.find((output) => output.status === "succeeded");
  const activeOutputId = selectedOutputId ?? firstReadyOutput?.output_id ?? null;

  return (
    <section className="generation-panel" aria-labelledby="generation-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">GENERATED VARIATIONS</p>
          <h2 id="generation-title">Pick the strongest scene.</h2>
        </div>
        <span className="file-rule">{status.progress.completed_outputs}/{status.progress.total_outputs} READY</span>
      </div>
      <div className="generation-grid">
        {status.outputs.map((output) => (
          <OutputCard
            key={output.output_id}
            output={output}
            selected={activeOutputId === output.output_id}
            onSelect={() => onSelectOutput(output.output_id)}
          />
        ))}
      </div>
    </section>
  );
}
