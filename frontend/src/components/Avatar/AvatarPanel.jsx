import React, { useEffect, useRef } from 'react';
import './AvatarPanel.css';

export default function AvatarPanel({ systemStatus }) {
  const canvasRef = useRef(null);

  // Draw static waveform baseline on mount
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Draw flat baseline
    ctx.strokeStyle = '#00C2A8';
    ctx.lineWidth = 1.5;
    ctx.shadowBlur = 8;
    ctx.shadowColor = '#00C2A8';

    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();
  }, []);

  const animClass = {
    idle: 'anim-breathe',
    listening: 'anim-shimmer',
    processing: 'anim-scan',
    speaking: 'anim-speaking',
    'out-of-scope': 'anim-oos',
  }[systemStatus] || 'anim-breathe';

  return (
    <div className="avatar-panel">
      <div className={`silhouette-wrapper ${animClass}`}>
        <svg
          className="silhouette"
          width="220"
          height="220"
          viewBox="0 0 220 220"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M110,20 a30,30 0 1,0 60,0 a30,30 0 1,0 -60,0M80,75 Q80,55 110,55 L140,55 Q175,55 175,75L185,160 Q185,170 175,170 L85,170 Q75,170 75,160 Z"
            fill="rgba(0, 194, 168, 0.10)"
            stroke="var(--teal)"
            strokeWidth="1.5"
          />
        </svg>
      </div>

      <canvas
        ref={canvasRef}
        className="waveform"
        width={360}
        height={40}
      />

      {systemStatus === 'out-of-scope' && (
        <span className="oos-label">⊘ OUT OF SCOPE</span>
      )}
    </div>
  );
}
