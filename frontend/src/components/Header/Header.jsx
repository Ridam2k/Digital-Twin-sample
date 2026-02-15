import React from 'react';
import { useLocation } from 'react-router-dom';
import NavTabs from '../Navigation/NavTabs.jsx';
import './Header.css';

export default function Header({ mode, systemStatus, showNav = false }) {
  const location = useLocation();
  const isObservability = location.pathname === '/observability';

  return (
    <header className="header">
      {/* Logomark */}
      <svg className="logomark" width="28" height="20" viewBox="0 0 28 20">
        <circle cx="8" cy="10" r="8" fill="var(--teal)" opacity="0.6" />
        <circle cx="20" cy="10" r="8" fill="none" stroke="var(--teal)" strokeWidth="1.5" />
      </svg>

      {/* Wordmark */}
      <div className="wordmark">
        <div className="wordmark-title">DIGITAL TWIN</div>
        {/* <div className="wordmark-subtitle"></div> */}
      </div>

      {/* Navigation Tabs */}
      {showNav && <NavTabs />}

      {/* Spacer */}
      <div className="spacer" />

      {/* Mode Badge - Only show on chat page */}
      {!isObservability && mode && (
        <span key={mode} className="mode-badge">
          [ {mode.toUpperCase()} ]
        </span>
      )}

      {/* Status Dot - Only show on chat page */}
      {!isObservability && systemStatus && (
        <div className={`status-dot status-${systemStatus}`} />
      )}
    </header>
  );
}
