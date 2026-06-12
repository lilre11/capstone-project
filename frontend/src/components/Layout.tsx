import { Link, useLocation } from 'react-router-dom';

export default function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();

  const links = [
    { to: '/', label: 'Home' },
    { to: '/phones', label: 'Smartphones' },
    { to: '/identify', label: 'Identify' },
    { to: '/preferences', label: 'Analyze' },
    { to: '/rankings', label: 'Rankings' },
    { to: '/model-performance', label: 'Model' },
    { to: '/chat', label: 'Chatbot' },
  ];

  return (
    <>
      <nav className="navbar">
        <Link to="/" className="navbar-brand">
          <span className="navbar-brand-icon" />
          SmartPick AI
        </Link>
        <ul className="navbar-links">
          {links.map((l) => (
            <li key={l.to}>
              <Link
                to={l.to}
                className={`navbar-link${pathname === l.to ? ' active' : ''}`}
              >
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <main className="page-wrapper">{children}</main>
      <footer className="footer">
        AI-Powered Smartphone Decision Support System — Capstone Project 2026
      </footer>
    </>
  );
}
