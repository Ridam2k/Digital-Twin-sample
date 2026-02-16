import React, { useEffect, useRef, useState } from 'react';
import { ingestGoogleDrive, ingestGithub } from '../../api/client.js';
import './AvatarPanel.css';

export default function AvatarPanel({ systemStatus }) {
  const canvasRef = useRef(null);

  // Ingestion state
  const [isIngestingGDrive, setIsIngestingGDrive] = useState(false);
  const [isIngestingGithub, setIsIngestingGithub] = useState(false);
  const [customRepo, setCustomRepo] = useState('');
  const [ingestError, setIngestError] = useState(null);
  const [ingestSuccess, setIngestSuccess] = useState(null); // 'gdrive' | 'github' | null

  // Hardcoded GITHUB_REPOS (synced with config.py)
  const GITHUB_REPOS = [
    "Ridam2k/EcoNest",
    "Ridam2k/FinDocSummariser",
    "Ridam2k/Udemy_contact-keeper",
    "Ridam2k/her-hygiene",
    "Ridam2k/user-groups-app"
  ];

  // Ingestion handlers
  const handleGDriveIngest = async () => {
    setIsIngestingGDrive(true);
    setIngestError(null);
    setIngestSuccess(null);
    try {
      const result = await ingestGoogleDrive();
      console.log('Google Drive ingestion complete:', result);
      setIngestSuccess('gdrive');
      setTimeout(() => setIngestSuccess(null), 3000);
    } catch (error) {
      console.error('Google Drive ingestion failed:', error);
      setIngestError(error.message || 'Google Drive ingestion failed');
    } finally {
      setIsIngestingGDrive(false);
    }
  };

  const handleGithubIngest = async () => {
    setIsIngestingGithub(true);
    setIngestError(null);
    setIngestSuccess(null);
    try {
      // Parse custom repo input
      const trimmedRepo = customRepo.trim();

      // Build repos array: add custom repo to config defaults if provided
      const customRepos = trimmedRepo
        ? [...GITHUB_REPOS, trimmedRepo]  // Add to config repos
        : null;  // Use config defaults only

      const result = await ingestGithub(customRepos);
      console.log('GitHub ingestion complete:', result);

      // Clear input on success
      setCustomRepo('');
      setIngestSuccess('github');
      setTimeout(() => setIngestSuccess(null), 3000);
    } catch (error) {
      console.error('GitHub ingestion failed:', error);
      setIngestError(error.message || 'GitHub ingestion failed');
    } finally {
      setIsIngestingGithub(false);
    }
  };

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
          width="350"
          height="390"
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

      {/* Ingestion controls section */}
      <div className="ingestion-controls">
        <button
          className="ingest-button"
          onClick={handleGDriveIngest}
          disabled={isIngestingGDrive || isIngestingGithub}
        >
          {isIngestingGDrive ? 'Ingesting...' : 'Ingest Google Drive'}
        </button>
        {ingestSuccess === 'gdrive' && (
          <span className="ingest-success">✓ Ingestion Complete!</span>
        )}

        <div className="github-ingest-group">
          <button
            className="ingest-button"
            onClick={handleGithubIngest}
            disabled={isIngestingGDrive || isIngestingGithub}
          >
            {isIngestingGithub ? 'Ingesting...' : 'Ingest Github'}
          </button>
          <input
            type="text"
            className="repo-input"
            placeholder="owner/repo (optional) for Ingest Github"
            value={customRepo}
            onChange={(e) => setCustomRepo(e.target.value)}
            disabled={isIngestingGDrive || isIngestingGithub}
          />
          {ingestSuccess === 'github' && (
            <span className="ingest-success">Ingestion Complete!</span>
          )}
        </div>

        {ingestError && (
          <div className="ingest-error">{ingestError}</div>
        )}
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
