import React from 'react';
import './ModeToast.css';

export default function ModeToast({ mode, routerScores }) {
  // Visibility is now controlled by parent (App.jsx)
  // This component simply renders when parent decides to show it
  return (
    <div className="mode-toast">
      <div className="toast-line">
        ⟳ Mode switched → <span className="toast-mode">{mode.toUpperCase()}</span>
      </div>
      <div className="toast-line">
        Confidence: {routerScores.technical.toFixed(2)} vs {routerScores.nontechnical.toFixed(2)}
      </div>
    </div>
  );
}
