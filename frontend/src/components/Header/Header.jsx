import React from 'react';
import './Header.css';

export default function Header({ mode, systemStatus }) {
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

      {/* Spacer */}
      <div className="spacer" />

      {/* Mode Badge */}
      <span key={mode} className="mode-badge">
        [ {mode.toUpperCase()} ]
      </span>

      {/* Status Dot */}
      <div className={`status-dot status-${systemStatus}`} />
    </header>
  );
}
