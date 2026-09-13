"use client";

import { useState } from "react";

import { BASE_NEGATIVE_PROMPT, DEFAULT_GENERATION_SETTINGS, SCENE_PRESETS } from "../lib/constants";
import type {
  GenerationSettings,
  GenerationHistoryItem,
  GenerationJobCreateResponse,
  GenerationJobStatusResponse,
  ImageMetadataResponse,
  ImageUploadResponse,
  JobResponse,
} from "../lib/types";

function restoredSetting(settings: Record<string, unknown>, key: keyof GenerationSettings): number {
  const value = settings[key];
  return typeof value === "number" ? value : DEFAULT_GENERATION_SETTINGS[key];
}

export type StudioPhase = "empty" | "uploading" | "uploaded" | "processing" | "generating" | "error";

export function useStudioState() {
  const [phase, setPhase] = useState<StudioPhase>("empty");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [image, setImage] = useState<ImageUploadResponse | null>(null);
  const [imageMetadata, setImageMetadata] = useState<ImageMetadataResponse | null>(null);
  const [preprocessingJob, setPreprocessingJob] = useState<JobResponse | null>(null);
  const [generationJobId, setGenerationJobId] = useState<string | null>(null);
  const [generationStatus, setGenerationStatus] = useState<GenerationJobStatusResponse | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<string>(SCENE_PRESETS[1].value);
  const [prompt, setPrompt] = useState<string>(SCENE_PRESETS[1].prompt);
  const [negativePrompt, setNegativePrompt] = useState<string>(BASE_NEGATIVE_PROMPT);
  const [variationCount, setVariationCount] = useState<3 | 4>(3);
  const [generationSettings, setGenerationSettings] = useState<GenerationSettings>({ ...DEFAULT_GENERATION_SETTINGS });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  function selectFile(file: File) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setImage(null);
    setImageMetadata(null);
    setPreprocessingJob(null);
    setGenerationJobId(null);
    setGenerationStatus(null);
    setErrorMessage(null);
    setPhase("empty");
  }

  function selectPreset(value: string) {
    const preset = SCENE_PRESETS.find((item) => item.value === value);
    setSelectedPreset(value);
    if (preset) setPrompt(preset.prompt);
  }

  function setGenerationSetting(key: keyof GenerationSettings, value: number) {
    setGenerationSettings((current) => ({ ...current, [key]: value }));
  }

  function beginUpload() {
    setErrorMessage(null);
    setPhase("uploading");
  }

  function finishUpload(uploadedImage: ImageUploadResponse) {
    setImage(uploadedImage);
    setImageMetadata(null);
    setPreprocessingJob(null);
    setGenerationJobId(null);
    setGenerationStatus(null);
    setErrorMessage(null);
    setPhase("uploaded");
  }

  function beginBackgroundRemoval() {
    setErrorMessage(null);
    setPhase("processing");
  }

  function finishBackgroundRemoval(job: JobResponse, metadata: ImageMetadataResponse) {
    setPreprocessingJob(job);
    setImageMetadata(metadata);
    setPhase(metadata.status === "failed" ? "error" : metadata.status === "ready" ? "uploaded" : "processing");
  }

  function beginGeneration() {
    setErrorMessage(null);
    setGenerationStatus(null);
    setPhase("generating");
  }

  function startGeneration(job: GenerationJobCreateResponse) {
    setGenerationJobId(job.job_id);
    setGenerationStatus(null);
    setPhase("generating");
  }

  function updateGenerationStatus(status: GenerationJobStatusResponse) {
    setGenerationStatus(status);
    if (status.status === "succeeded" || status.status === "partially_succeeded") setPhase("uploaded");
    if (status.status === "failed" || status.status === "cancelled") {
      setErrorMessage(status.error_message ?? "Generation failed. Try again.");
      setPhase("error");
    }
  }

  function failGeneration(message: string) {
    setErrorMessage(message);
    setPhase("error");
  }

  function failBackgroundRemoval(message: string) {
    setErrorMessage(message);
    setPhase("error");
  }

  function updateImageMetadata(metadata: ImageMetadataResponse) {
    setImageMetadata(metadata);
    if (metadata.status === "ready" || metadata.status === "uploaded") setPhase("uploaded");
    if (metadata.status === "failed") {
      setErrorMessage("Background removal failed. Try again.");
      setPhase("error");
    }
  }

  function failUpload(message: string) {
    setErrorMessage(message);
    setPhase("error");
  }

  function restoreHistory(item: GenerationHistoryItem) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(null);
    setPreviewUrl(null);
    setImage({
      image_id: item.image_id,
      status: "ready",
      original_url: item.original_url,
      width: item.width ?? 0,
      height: item.height ?? 0,
      mime_type: item.mime_type ?? "image/jpeg",
    });
    setImageMetadata({
      image_id: item.image_id,
      status: "ready",
      original_url: item.original_url,
      mask_url: null,
      cutout_url: item.cutout_url,
      width: item.width ?? 0,
      height: item.height ?? 0,
      mime_type: item.mime_type ?? "image/jpeg",
      metadata: {},
    });
    setPreprocessingJob(null);
    setGenerationJobId(item.job_id);
    setGenerationStatus({
      job_id: item.job_id,
      image_id: item.image_id,
      status: item.status,
      progress: {
        completed_outputs: item.outputs.filter((output) => output.status === "succeeded").length,
        total_outputs: item.variation_count ?? item.outputs.length,
      },
      outputs: item.outputs.map((output) => ({
        output_id: output.output_id,
        status: output.status,
        url: output.url ?? output.thumbnail_url ?? "",
        download_url: output.download_url ?? "",
        seed: output.seed,
      })),
      error_message: item.error_message,
    });
    if (item.scene_preset) setSelectedPreset(item.scene_preset);
    setPrompt(item.prompt ?? "professional product photography");
    setNegativePrompt(item.negative_prompt ?? BASE_NEGATIVE_PROMPT);
    setVariationCount(item.variation_count === 4 ? 4 : 3);
    setGenerationSettings({
      steps: restoredSetting(item.settings, "steps"),
      guidance_scale: restoredSetting(item.settings, "guidance_scale"),
      strength: restoredSetting(item.settings, "strength"),
      controlnet_conditioning_scale: restoredSetting(item.settings, "controlnet_conditioning_scale"),
      canvas_size: restoredSetting(item.settings, "canvas_size"),
    });
    setErrorMessage(null);
    setPhase("uploaded");
  }

  return {
    phase,
    selectedFile,
    previewUrl,
    image,
    imageMetadata,
    preprocessingJob,
    generationJobId,
    generationStatus,
    selectedPreset,
    prompt,
    negativePrompt,
    variationCount,
    generationSettings,
    errorMessage,
    selectFile,
    selectPreset,
    setPrompt,
    setNegativePrompt,
    setVariationCount,
    setGenerationSetting,
    beginUpload,
    finishUpload,
    beginBackgroundRemoval,
    finishBackgroundRemoval,
    beginGeneration,
    startGeneration,
    updateGenerationStatus,
    failGeneration,
    failBackgroundRemoval,
    updateImageMetadata,
    failUpload,
    restoreHistory,
  };
}
