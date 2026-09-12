"use client";

import type { CSSProperties, ChangeEvent } from "react";
import { useState } from "react";

type BeforeAfterComparisonProps = {
  beforeUrl: string;
  afterUrl: string;
  beforeLabel: string;
  afterLabel: string;
};

export function BeforeAfterComparison({ beforeUrl, afterUrl, beforeLabel, afterLabel }: BeforeAfterComparisonProps) {
  const [position, setPosition] = useState(50);
  const comparisonStyle = { "--comparison-position": `${position}%` } as CSSProperties;

  function handlePositionChange(event: ChangeEvent<HTMLInputElement>) {
    setPosition(Number(event.target.value));
  }

  return (
    <section className="before-after-panel" aria-labelledby="before-after-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">COMPARISON</p>
          <h2 id="before-after-title">Review the transformation.</h2>
        </div>
        <span className="file-rule">DRAG OR USE ARROW KEYS</span>
      </div>
      <div className="before-after" style={comparisonStyle}>
        <img className="before-after-image after-image" src={afterUrl} alt={afterLabel} />
        <div className="before-image-clip">
          <img className="before-after-image" src={beforeUrl} alt={beforeLabel} />
        </div>
        <div className="before-after-label before-label">{beforeLabel}</div>
        <div className="before-after-label after-label">{afterLabel}</div>
        <div className="before-after-divider" aria-hidden="true">
          <span className="before-after-handle" />
        </div>
        <label className="before-after-control">
          <span className="sr-only">Show more of the {beforeLabel.toLowerCase()} image</span>
          <input
            type="range"
            min="0"
            max="100"
            value={position}
            aria-label={`Comparison position: ${position}%`}
            onChange={handlePositionChange}
          />
        </label>
      </div>
    </section>
  );
}
