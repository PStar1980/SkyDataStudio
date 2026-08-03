function Icon({ children }) {
  return <span className="topbar-icon-glyph" aria-hidden="true">{children}</span>;
}

function Topbar({ pageTitle, pageSubtitle, onMenu }) {
  return (
    <header className="studio-topbar">
      <button className="mobile-menu-button" type="button" onClick={onMenu} aria-label="Open menu">
        ☰
      </button>
      <div className="topbar-page-copy">
        <strong>{pageTitle}</strong>
        <span>{pageSubtitle}</span>
      </div>
      <label className="command-search">
        <Icon>⌕</Icon>
        <input aria-label="Command search" placeholder="Search assets, pipelines, models…" />
        <kbd>Ctrl K</kbd>
      </label>
      <div className="topbar-actions">
        <button type="button" aria-label="Data quality notifications"><Icon>✦</Icon><span className="action-count">2</span></button>
        <button type="button" aria-label="Messages"><Icon>◇</Icon></button>
        <button type="button" className="operator-button" aria-label="Operator menu">PS</button>
      </div>
    </header>
  );
}

export default Topbar;
