function PlaceholderPage({ title, subtitle }) {
  return (
    <div className="page-stack">
      <section className="page-intro">
        <span className="eyebrow">PLANNED WORKBENCH SURFACE</span>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </section>
      <section className="panel empty-workspace">
        <div className="empty-symbol">◇</div>
        <h2>{title} enters in a later roadmap phase.</h2>
        <p>The navigation and design-system seam is ready; data contracts and working behavior will be added phase by phase.</p>
      </section>
    </div>
  );
}

export default PlaceholderPage;
