import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard', icon: '📊' },
  { to: '/channels', label: 'Channels', icon: '📡' },
  { to: '/summaries', label: 'Summaries', icon: '📄' },
  { to: '/email', label: 'Email Settings', icon: '📧' },
];

export default function Sidebar() {
  return (
    <div className="sidebar">
      <div className="sidebar-header">YT Summarizer</div>
      <nav>
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
