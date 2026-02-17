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
  const [projects, setProjects] = useState({
    technical: { code: [], documentation: [] },
    nontechnical: { all: [] },
  });
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectsError, setProjectsError] = useState(null);

  // Hardcoded GITHUB_REPOS (synced with config.py)
  const GITHUB_REPOS = [
    "Ridam2k/EcoNest",
    "Ridam2k/FinDocSummariser",
    "Ridam2k/Udemy_contact-keeper",
    "Ridam2k/her-hygiene",
    "Ridam2k/user-groups-app",
    "Ridam2k/BinaryNeuralNetworks"
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
        // Normalize items: accept both {title, url} objects and plain strings
        const normalize = (arr) =>
          (Array.isArray(arr) ? arr : []).map((item) =>
            typeof item === 'string' ? { title: item, url: '' } : item
          );
        if (data && data.groups) {
          setProjects({
            technical: {
              code: normalize(data.groups?.technical?.code),
              documentation: normalize(data.groups?.technical?.documentation),
            },
            nontechnical: {
              all: normalize(data.groups?.nontechnical?.all),
            },
          });
        } else if (Array.isArray(data.projects)) {
          setProjects({
            technical: { code: [], documentation: [] },
            nontechnical: { all: normalize(data.projects) },
          });
        } else {
          setProjects({
            technical: { code: [], documentation: [] },
            nontechnical: { all: [] },
          });
        }
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
        {!projectsLoading && !projectsError &&
          projects.technical.code.length === 0 &&
          projects.technical.documentation.length === 0 &&
          projects.nontechnical.all.length === 0 && (
          <div className="projects-empty">No projects found.</div>
        )}
        {!projectsLoading && !projectsError && (
          <div className="projects-grid">
            <div className="projects-col">
              <div className="projects-col-title">Technical</div>
              <div className="projects-subgroup">
                <div className="projects-subtitle">Code</div>
                {projects.technical.code.length === 0 ? (
                  <div className="projects-empty">No code projects.</div>
                ) : (
                  <ul className="projects-list">
                    {projects.technical.code.map((item) => (
                      <li key={`tech-code-${item.title}`} className="projects-item">
                        {item.url ? (
                          <a href={item.url} target="_blank" rel="noopener noreferrer" className="projects-link">
                            {item.title}
                          </a>
                        ) : item.title}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="projects-subgroup">
                <div className="projects-subtitle">Writeups</div>
                {projects.technical.documentation.length === 0 ? (
                  <div className="projects-empty">No documentation projects.</div>
                ) : (
                  <ul className="projects-list">
                    {projects.technical.documentation.map((item) => (
                      <li key={`tech-doc-${item.title}`} className="projects-item">
                        {item.url ? (
                          <a href={item.url} target="_blank" rel="noopener noreferrer" className="projects-link">
                            {item.title}
                          </a>
                        ) : item.title}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <div className="projects-col">
              <div className="projects-col-title">Non-Technical</div>
              {projects.nontechnical.all.length === 0 ? (
                <div className="projects-empty">No non-technical projects.</div>
              ) : (
                <ul className="projects-list">
                  {projects.nontechnical.all.map((item) => (
                    <li key={`nontech-${item.title}`} className="projects-item">
                      {item.url ? (
                        <a href={item.url} target="_blank" rel="noopener noreferrer" className="projects-link">
                          {item.title}
                        </a>
                      ) : item.title}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
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
