function StatusPill({ status, tone }) {
  const normalized = String(tone || status || 'PLANNED').toLowerCase();
  return <span className={`status-pill status-${normalized}`}>{status}</span>;
}

export default StatusPill;
