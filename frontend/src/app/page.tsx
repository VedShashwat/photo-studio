import { ImageUpload } from "../components/image-upload/image-upload";

export default function Home() {
  return (
    <main className="studio-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AI PRODUCT PHOTOGRAPHY</p>
          <h1>Studio workspace</h1>
        </div>
        <span className="status-badge">Local workspace</span>
      </header>
      <section className="workspace" aria-label="Product photography workspace">
        <div className="workspace-copy">
          <p className="eyebrow">PRODUCT SOURCE</p>
          <h2>Make the product the focus.</h2>
          <p>Bring in one clean source image. The studio will preserve its identity as the scene evolves.</p>
        </div>
        <ImageUpload />
      </section>
    </main>
  );
}
