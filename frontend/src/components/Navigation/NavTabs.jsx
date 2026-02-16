import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './NavTabs.css';

export default function NavTabs() {
  const location = useLocation();
  const currentPath = location.pathname;

  return (
    <nav className="nav-tabs">
      <Link
        to="/"
        className={`nav-tab ${currentPath === '/' ? 'active' : ''}`}
      >
        CHAT
      </Link>
      <Link
        to="/observability"
        className={`nav-tab ${currentPath === '/observability' ? 'active' : ''}`}
      >
        OBSERVABILITY
      </Link>
    </nav>
  );
}
