import { useMemo, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import BrandMark from './BrandMark.jsx';

const GROUPS = [
  {
    label: 'Dashboards',
    icon: '◈',
    items: [{ label: 'Studio Overview', to: '/dashboard', icon: '⌘' }],
  },
  {
    label: 'Data Workspace',
    icon: '◇',
    items: [
      { label: 'Data Assets', to: '/workspace/assets', icon: '▱' },
      { label: 'Metadata Registry', to: '/workspace/registry', icon: '▤' },
      { label: 'Source Mappings', to: '/workspace/mappings', icon: '⌁' },
      { label: 'Pipelines', to: '/workspace/pipelines', icon: '⇢' },
      { label: 'Transformations', to: '/workspace/transformations', icon: '⟲' },
      { label: 'Data Models', to: '/workspace/models', icon: '⬡' },
    ],
  },
  {
    label: 'Orchestration',
    icon: '◎',
    items: [
      { label: 'Apache Airflow', to: '/orchestration/airflow', icon: '◌' },
      { label: 'Pipeline Runs', to: '/orchestration/runs', icon: '↺' },
      { label: 'Schedules & Backfills', to: '/orchestration/backfills', icon: '◷' },
    ],
  },
  {
    label: 'Quality & Lineage',
    icon: '✦',
    items: [
      { label: 'Data Quality', to: '/quality/checks', icon: '✓' },
      { label: 'Contracts', to: '/quality/contracts', icon: '▤' },
      { label: 'Lineage', to: '/quality/lineage', icon: '⌁' },
    ],
  },
  {
    label: 'Analytics Delivery',
    icon: '△',
    items: [
      { label: 'Analytical Marts', to: '/delivery/marts', icon: '▦' },
      { label: 'Semantic Layer', to: '/delivery/semantic', icon: '∑' },
      { label: 'Reports', to: '/delivery/reports', icon: '▥' },
      { label: 'Power BI', to: '/delivery/power-bi', icon: '▰' },
    ],
  },
  {
    label: 'Configuration',
    icon: '⚙',
    items: [
      { label: 'Connections', to: '/configuration/connections', icon: '↔' },
      { label: 'Environments', to: '/configuration/environments', icon: '◫' },
      { label: 'Settings', to: '/configuration/settings', icon: '⋯' },
    ],
  },
];

function Sidebar({ mobileOpen, onClose }) {
  const location = useLocation();
  const navigate = useNavigate();
  const activeGroup = useMemo(
    () => GROUPS.find((group) => group.items.some((item) => location.pathname === item.to))?.label,
    [location.pathname],
  );
  const [expanded, setExpanded] = useState(activeGroup ?? 'Dashboards');

  function selectGroup(group) {
    setExpanded(group.label);
    if (!group.items.some((item) => location.pathname === item.to)) {
      navigate(group.items[0].to);
    }
  }

  return (
    <aside className={`studio-sidebar ${mobileOpen ? 'is-open' : ''}`}>
      <div className="sidebar-aurora" aria-hidden="true" />
      <div className="sidebar-brand-row">
        <NavLink to="/dashboard" className="sidebar-brand" onClick={onClose}>
          <BrandMark />
        </NavLink>
        <button className="sidebar-close" type="button" onClick={onClose} aria-label="Close menu">
          ×
        </button>
      </div>
      <nav className="sidebar-nav" aria-label="SkyData Studio navigation">
        {GROUPS.map((group) => {
          const isExpanded = expanded === group.label;
          return (
            <section className={`nav-group ${isExpanded ? 'is-expanded' : ''}`} key={group.label}>
              <button className="nav-group-button" type="button" onClick={() => selectGroup(group)}>
                <span className="nav-group-icon">{group.icon}</span>
                <span>{group.label}</span>
                <span className="nav-chevron">›</span>
              </button>
              <div className="nav-group-panel" aria-hidden={!isExpanded}>
                <div className="nav-group-items">
                  {group.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={onClose}
                      className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                      tabIndex={isExpanded ? undefined : -1}
                    >
                      <span className="nav-link-icon">{item.icon}</span>
                      <span>{item.label}</span>
                    </NavLink>
                  ))}
                </div>
              </div>
            </section>
          );
        })}
      </nav>
      <div className="sidebar-footer">
        <span className="environment-dot" />
        <span>
          <strong>Development</strong>
          <small>Phase 7.1 dbt quality evidence</small>
        </span>
      </div>
    </aside>
  );
}

export default Sidebar;
