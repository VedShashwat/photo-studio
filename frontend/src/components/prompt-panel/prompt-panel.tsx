"use client";

import { ChangeEvent } from "react";

import { SCENE_PRESETS } from "../../lib/constants";
import type { GenerationSettings } from "../../lib/types";

type PromptPanelProps = {
  selectedPreset: string;
  prompt: string;
  negativePrompt: string;
  variationCount: 3 | 4;
  generationSettings: GenerationSettings;
  canGenerate: boolean;
  isGenerating: boolean;
  onGenerate: () => void;
  onPresetChange: (value: string) => void;
  onPromptChange: (value: string) => void;
  onNegativePromptChange: (value: string) => void;
  onVariationCountChange: (value: 3 | 4) => void;
  onGenerationSettingChange: (key: keyof GenerationSettings, value: number) => void;
};

export function PromptPanel({
  selectedPreset,
  prompt,
  negativePrompt,
  variationCount,
  generationSettings,
  canGenerate,
  isGenerating,
  onGenerate,
  onPresetChange,
  onPromptChange,
  onNegativePromptChange,
  onVariationCountChange,
  onGenerationSettingChange,
}: PromptPanelProps) {
  function handleVariationChange(event: ChangeEvent<HTMLSelectElement>) {
    onVariationCountChange(Number(event.target.value) as 3 | 4);
  }

  return (
    <section className="prompt-panel" aria-labelledby="prompt-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">SCENE DIRECTION</p>
          <h2 id="prompt-title">Choose the marketing context.</h2>
        </div>
        <span className="file-rule">3–4 VARIATIONS</span>
      </div>
      <label className="field-label" htmlFor="scene-preset">Scene preset</label>
      <select id="scene-preset" className="field-control" value={selectedPreset} onChange={(event) => onPresetChange(event.target.value)}>
        {SCENE_PRESETS.map((preset) => <option key={preset.value} value={preset.value}>{preset.label}</option>)}
      </select>
      <label className="field-label" htmlFor="scene-prompt">Prompt</label>
      <textarea
        id="scene-prompt"
        className="field-control field-textarea"
        value={prompt}
        maxLength={500}
        onChange={(event) => onPromptChange(event.target.value)}
      />
      <div className="field-row">
        <div>
          <label className="field-label" htmlFor="negative-prompt">Negative prompt</label>
          <textarea
            id="negative-prompt"
            className="field-control field-textarea"
            value={negativePrompt}
            maxLength={500}
            onChange={(event) => onNegativePromptChange(event.target.value)}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="variation-count">Variations</label>
          <select id="variation-count" className="field-control" value={variationCount} onChange={handleVariationChange}>
            <option value={3}>3 outputs</option>
            <option value={4}>4 outputs</option>
          </select>
        </div>
      </div>
      <div className="settings-grid">
        <label className="setting-field" htmlFor="generation-steps">
          <span className="setting-heading"><span>Quality steps</span><output>{generationSettings.steps}</output></span>
          <select
            id="generation-steps"
            className="field-control"
            value={generationSettings.steps}
            onChange={(event) => onGenerationSettingChange("steps", Number(event.target.value))}
          >
            <option value={20}>20 steps</option>
            <option value={25}>25 steps</option>
            <option value={30}>30 steps</option>
            <option value={40}>40 steps</option>
          </select>
        </label>
        <label className="setting-field" htmlFor="scene-strength">
          <span className="setting-heading"><span>Scene change</span><output>{generationSettings.strength.toFixed(2)}</output></span>
          <input
            id="scene-strength"
            type="range"
            min="0.35"
            max="0.95"
            step="0.05"
            value={generationSettings.strength}
            onChange={(event) => onGenerationSettingChange("strength", Number(event.target.value))}
          />
        </label>
        <label className="setting-field" htmlFor="prompt-guidance">
          <span className="setting-heading"><span>Prompt guidance</span><output>{generationSettings.guidance_scale.toFixed(1)}</output></span>
          <input
            id="prompt-guidance"
            type="range"
            min="4"
            max="10"
            step="0.5"
            value={generationSettings.guidance_scale}
            onChange={(event) => onGenerationSettingChange("guidance_scale", Number(event.target.value))}
          />
        </label>
        <label className="setting-field" htmlFor="structure-scale">
          <span className="setting-heading"><span>Product structure</span><output>{generationSettings.controlnet_conditioning_scale.toFixed(2)}</output></span>
          <input
            id="structure-scale"
            type="range"
            min="0.2"
            max="1"
            step="0.05"
            value={generationSettings.controlnet_conditioning_scale}
            onChange={(event) => onGenerationSettingChange("controlnet_conditioning_scale", Number(event.target.value))}
          />
        </label>
      </div>
      <div className="generation-actions">
        <button type="button" className="primary-button" onClick={onGenerate} disabled={!canGenerate || isGenerating}>
          {isGenerating ? "Generating variations..." : canGenerate ? "Generate variations" : "Remove the background first"}
        </button>
      </div>
    </section>
  );
}
