"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";

import {
  ApiClientError,
  apiUrl,
  createGenerationJob,
  getImage,
  requestBackgroundRemoval,
  uploadImage,
} from "../../lib/api-client";
import { useGenerationPolling } from "../../hooks/use-generation-polling";
import { usePreprocessingPolling } from "../../hooks/use-preprocessing-polling";
import { useStudioState } from "../../hooks/use-studio-state";
import { BeforeAfterComparison } from "../before-after/before-after";
import { HistoryPanel } from "../history/history-panel";
import { GenerationGrid } from "../generation-grid/generation-grid";
import { PromptPanel } from "../prompt-panel/prompt-panel";
import { CutoutPreview } from "../studio/cutout-preview";

const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

function validateFile(file: File): string | null {
  if (!ACCEPTED_TYPES.has(file.type)) return "Choose a JPEG, PNG, or WebP image.";
  if (file.size > MAX_UPLOAD_BYTES) return "Image must be smaller than 15 MB.";
  return null;
}

export function ImageUpload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedOutputId, setSelectedOutputId] = useState<string | null>(null);
  const state = useStudioState();
  usePreprocessingPolling(
    state.image?.image_id ?? null,
    state.phase === "processing",
    state.updateImageMetadata,
    state.failBackgroundRemoval,
  );
  useGenerationPolling(
    state.generationJobId,
    state.phase === "generating",
    state.updateGenerationStatus,
    state.failGeneration,
  );

  function handleFile(file: File | undefined) {
    if (!file) return;
    const validationError = validateFile(file);
    if (validationError) {
      state.failUpload(validationError);
      return;
    }
    setSelectedOutputId(null);
    state.selectFile(file);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    handleFile(event.target.files?.[0]);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    handleFile(event.dataTransfer.files[0]);
  }

  async function handleUpload() {
    if (!state.selectedFile) return;
    state.beginUpload();
    try {
      state.finishUpload(await uploadImage(state.selectedFile));
    } catch (error) {
      const message = error instanceof ApiClientError ? error.message : "Upload failed. Try again.";
      state.failUpload(message);
    }
  }

  async function handleGenerate() {
    if (!state.image || state.imageMetadata?.status !== "ready") return;
    setSelectedOutputId(null);
    state.beginGeneration();
    try {
      const job = await createGenerationJob({
        image_id: state.image.image_id,
        scene_preset: state.selectedPreset,
        prompt: state.prompt,
        negative_prompt: state.negativePrompt,
        variation_count: state.variationCount,
        settings: state.generationSettings,
      });
      state.startGeneration(job);
    } catch (error) {
      const message = error instanceof ApiClientError ? error.message : "Generation failed. Try again.";
      state.failGeneration(message);
    }
  }

  async function handleRemoveBackground() {
    if (!state.image) return;
    state.beginBackgroundRemoval();
    try {
      const job = await requestBackgroundRemoval(state.image.image_id);
      const metadata = await getImage(state.image.image_id);
      state.finishBackgroundRemoval(job, metadata);
    } catch (error) {
      const message = error instanceof ApiClientError ? error.message : "Background removal failed. Try again.";
      state.failBackgroundRemoval(message);
    }
  }

  const readyOutput = state.generationStatus?.outputs.find(
    (output) => output.output_id === selectedOutputId && output.status === "succeeded",
  ) ?? state.generationStatus?.outputs.find((output) => output.status === "succeeded");
  const comparisonBeforeUrl = state.imageMetadata?.cutout_url
    ? apiUrl(state.imageMetadata.cutout_url)
    : state.image
      ? apiUrl(state.image.original_url)
      : null;
  const comparisonBeforeLabel = state.imageMetadata?.cutout_url ? "Product cutout" : "Original upload";
  const sourcePreviewUrl = state.previewUrl ?? (state.image ? apiUrl(state.image.original_url) : null);

  return (
    <section className="upload-panel" aria-labelledby="upload-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">SOURCE IMAGE</p>
          <h2 id="upload-title">Start with a product photo.</h2>
        </div>
        <span className="file-rule">JPEG / PNG / WEBP / 512PX+ / 15 MB</span>
      </div>

      <div
        className={`upload-zone${isDragging ? " is-dragging" : ""}${sourcePreviewUrl ? " has-preview" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); setIsDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => { if (event.currentTarget === event.target) setIsDragging(false); }}
        onDrop={handleDrop}
      >
        {sourcePreviewUrl ? (
          <div className="preview-stage">
            <img src={sourcePreviewUrl} alt="Selected product preview" />
            <div className="preview-meta">
              <strong>{state.selectedFile?.name ?? "Restored product source"}</strong>
              <span>
                {state.selectedFile
                  ? `${(state.selectedFile.size / 1024 / 1024).toFixed(1)} MB`
                  : state.image
                    ? `${state.image.width} x ${state.image.height}px`
                    : ""}
              </span>
            </div>
          </div>
        ) : (
          <div className="drop-message">
            <span className="upload-icon" aria-hidden="true">+</span>
            <strong>Drop an image here</strong>
            <span>or choose a file from this device</span>
          </div>
        )}
        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={handleInputChange} hidden />
      </div>

      <div className="upload-actions">
        <button type="button" className="secondary-button" onClick={() => inputRef.current?.click()}>
          {sourcePreviewUrl ? "Choose another" : "Choose image"}
        </button>
        <button type="button" className="primary-button" onClick={handleUpload} disabled={!state.selectedFile || state.phase === "uploading"}>
          {state.phase === "uploading" ? "Uploading..." : "Upload image"}
        </button>
      </div>

      {state.phase === "uploaded" && state.image ? (
        <p className="success-message" role="status">Uploaded at {state.image.width} x {state.image.height}px.</p>
      ) : null}
      {state.image ? (
        <div className="processing-actions">
          <button
            type="button"
            className="primary-button"
            onClick={handleRemoveBackground}
            disabled={state.phase === "processing" || state.imageMetadata?.status === "ready"}
          >
            {state.phase === "processing" ? "Removing background..." : state.imageMetadata?.status === "ready" ? "Background removed" : "Remove background"}
          </button>
          {state.preprocessingJob ? <span>Job {state.preprocessingJob.status}</span> : null}
        </div>
      ) : null}
      {state.image ? (
        <CutoutPreview
          originalUrl={apiUrl(state.image.original_url)}
          cutoutUrl={state.imageMetadata?.cutout_url ? apiUrl(state.imageMetadata.cutout_url) : null}
          status={state.imageMetadata?.status ?? state.image.status}
        />
      ) : null}
      {state.generationStatus ? (
        <>
          <p className="success-message" role="status">
            Generation {state.generationStatus.status}: {state.generationStatus.progress.completed_outputs}/{state.generationStatus.progress.total_outputs} outputs.
          </p>
          <GenerationGrid
            status={state.generationStatus}
            selectedOutputId={selectedOutputId}
            onSelectOutput={setSelectedOutputId}
          />
          {readyOutput && comparisonBeforeUrl ? (
            <BeforeAfterComparison
              beforeUrl={comparisonBeforeUrl}
              afterUrl={apiUrl(readyOutput.url)}
              beforeLabel={comparisonBeforeLabel}
              afterLabel="Generated scene"
            />
          ) : null}
        </>
      ) : null}
      <PromptPanel
        selectedPreset={state.selectedPreset}
        prompt={state.prompt}
        negativePrompt={state.negativePrompt}
        variationCount={state.variationCount}
        generationSettings={state.generationSettings}
        canGenerate={state.imageMetadata?.status === "ready"}
        isGenerating={state.phase === "generating"}
        onGenerate={handleGenerate}
        onPresetChange={state.selectPreset}
        onPromptChange={state.setPrompt}
        onNegativePromptChange={state.setNegativePrompt}
        onVariationCountChange={state.setVariationCount}
        onGenerationSettingChange={state.setGenerationSetting}
      />
      {state.errorMessage ? <p className="error-message" role="alert">{state.errorMessage}</p> : null}
      <HistoryPanel
        onRestore={state.restoreHistory}
        refreshKey={`${state.generationStatus?.job_id ?? ""}:${state.generationStatus?.status ?? ""}`}
      />
    </section>
  );
}
