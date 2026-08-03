function StatusPill({ status }) {
  const normalized = String(status || 'PLANNED').toLowerCase();
  return <span className={`status-pill status-${normalized}`}>{status}</span>;
}

export default StatusPill;
