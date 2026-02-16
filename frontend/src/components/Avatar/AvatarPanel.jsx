import React, { useEffect, useRef, useState } from 'react';
import { ingestGoogleDrive, ingestGithub, fetchProjects } from '../../api/client.js';
import './AvatarPanel.css';

export default function AvatarPanel({ systemStatus }) {
  const canvasRef = useRef(null);

  // Ingestion state
  const [isIngestingGDrive, setIsIngestingGDrive] = useState(false);
  const [isIngestingGithub, setIsIngestingGithub] = useState(false);
  const [customRepo, setCustomRepo] = useState('');
  const [ingestError, setIngestError] = useState(null);
  const [ingestSuccess, setIngestSuccess] = useState(null); // 'gdrive' | 'github' | null

  // Projects list state
  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectsError, setProjectsError] = useState(null);

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

  // Fetch available projects once on mount
  useEffect(() => {
    let isMounted = true;

    const loadProjects = async () => {
      setProjectsLoading(true);
      setProjectsError(null);
      try {
        const data = await fetchProjects();
        if (!isMounted) return;
        setProjects(Array.isArray(data.projects) ? data.projects : []);
      } catch (error) {
        if (!isMounted) return;
        setProjectsError(error.message || 'Failed to load projects');
      } finally {
        if (isMounted) {
          setProjectsLoading(false);
        }
      }
    };

    loadProjects();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="avatar-panel">
      <div className="projects-panel">
        <div className="projects-title">Available Projects</div>
        {projectsLoading && (
          <div className="projects-status">Loading...</div>
        )}
        {projectsError && (
          <div className="projects-error">{projectsError}</div>
        )}
        {!projectsLoading && !projectsError && projects.length === 0 && (
          <div className="projects-empty">No projects found.</div>
        )}
        {!projectsLoading && !projectsError && projects.length > 0 && (
          <ul className="projects-list">
            {projects.map((title) => (
              <li key={title} className="projects-item">
                {title}
              </li>
            ))}
          </ul>
        )}
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
