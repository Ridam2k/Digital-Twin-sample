import React, { useState, useEffect } from 'react';
import MetricsCard from './MetricsCard.jsx';
import { fetchRetrievalStats } from '../../api/client.js';
import './RetrievalPanel.css';

export default function RetrievalPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRecomputing, setIsRecomputing] = useState(false);

  const loadStats = async (recompute = false) => {
    if (recompute) {
      setIsRecomputing(true);
    }

    try {
      const result = await fetchRetrievalStats(recompute);
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load retrieval stats');
    } finally {
      setLoading(false);
      setIsRecomputing(false);
    }
  };

  useEffect(() => {
    loadStats(false);
  }, []);

  const handleRecompute = () => {
    loadStats(true);
  };

  return (
    <MetricsCard title="Retrieval Performance" loading={loading} error={error}>
      {data && (
        <>
          <div className="metric-section">
            <div className="section-header">Overall</div>
            <div className="metric-row">
              <span className="metric-label">Recall@{data.overall.k}</span>
              <span className="metric-value score-good">
                {data.overall.recall_at_k.toFixed(4)}
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">MRR@{data.overall.k}</span>
              <span className="metric-value score-good">
                {data.overall.mrr_at_k.toFixed(4)}
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">Queries Evaluated</span>
              <span className="metric-value-neutral">
                {data.overall.total_queries}
              </span>
            </div>
          </div>

          {Object.entries(data.by_namespace).map(([ns, stats]) => (
            <div key={ns} className="metric-section">
              <div className="section-header">{ns} ({stats.count} queries)</div>
              <div className="metric-row">
                <span className="metric-label">Recall@{data.overall.k}</span>
                <span className="metric-value score-good">
                  {stats.recall_at_k.toFixed(4)}
                </span>
              </div>
              <div className="metric-row">
                <span className="metric-label">MRR@{data.overall.k}</span>
                <span className="metric-value score-good">
                  {stats.mrr_at_k.toFixed(4)}
                </span>
              </div>
            </div>
          ))}

          <button
            className="recompute-button"
            onClick={handleRecompute}
            disabled={isRecomputing}
          >
            {isRecomputing ? 'Recomputing...' : 'Recompute Metrics'}
          </button>

          <div className="metadata-note">
            Computed at: {new Date(data.metadata.computed_at).toLocaleString()}
          </div>
        </>
      )}
    </MetricsCard>
  );
}
