import type { ImageStatus } from "../../lib/types";

type CutoutPreviewProps = {
  originalUrl: string;
  cutoutUrl: string | null;
  status: ImageStatus;
};

export function CutoutPreview({ originalUrl, cutoutUrl, status }: CutoutPreviewProps) {
  const statusLabel = status === "ready" ? "READY" : status === "uploaded" ? "ACTION NEEDED" : status.toUpperCase();

  return (
    <section className="cutout-panel" aria-labelledby="cutout-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">PRODUCT ISOLATION</p>
          <h2 id="cutout-title">Keep the product, change the scene.</h2>
        </div>
        <span className="file-rule">{statusLabel}</span>
      </div>
      <div className="comparison-grid">
        <figure className="comparison-card">
          <figcaption>Original upload</figcaption>
          <img src={originalUrl} alt="Original uploaded product" />
        </figure>
        <figure className={`comparison-card${cutoutUrl ? "" : " is-pending"}`}>
          <figcaption>Product cutout</figcaption>
          {cutoutUrl ? (
            <img src={cutoutUrl} alt="Product with background removed" />
          ) : (
            <div className="cutout-placeholder" role="status">
              <strong>
                {status === "failed"
                  ? "Background removal failed"
                  : status === "uploaded"
                    ? "Ready for background removal"
                    : "Cutout is being prepared"}
              </strong>
              <span>
                {status === "uploaded"
                  ? "Choose Remove background above to start preprocessing."
                  : "The isolated product will appear here when preprocessing finishes."}
              </span>
            </div>
          )}
        </figure>
      </div>
    </section>
  );
}
