function BrandMark({ compact = false }) {
  return (
    <div className={`brand-lockup ${compact ? 'is-compact' : ''}`}>
      <svg className="brand-symbol" viewBox="0 0 64 64" role="img" aria-label="SkyData Studio">
        <defs>
          <linearGradient id="studioGradient" x1="10" x2="54" y1="8" y2="58">
            <stop offset="0" stopColor="#8bf5dc" />
            <stop offset="0.55" stopColor="#42d9c6" />
            <stop offset="1" stopColor="#9a83ff" />
          </linearGradient>
        </defs>
        <path d="M32 4 55 17v30L32 60 9 47V17Z" fill="none" stroke="url(#studioGradient)" strokeWidth="2.4" />
        <path d="M20 22c0-4 24-4 24 0s-24 4-24 0Zm0 0v9c0 4 24 4 24 0v-9m-24 9v9c0 4 24 4 24 0v-9" fill="none" stroke="url(#studioGradient)" strokeLinecap="round" strokeWidth="2.7" />
        <path d="m26 47 6 4 6-4" fill="none" stroke="#f3bd55" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.4" />
      </svg>
      {!compact ? (
        <span className="brand-copy">
          <strong>SkyData Studio</strong>
          <small>Data Engineering Workbench</small>
        </span>
      ) : null}
    </div>
  );
}

export default BrandMark;
