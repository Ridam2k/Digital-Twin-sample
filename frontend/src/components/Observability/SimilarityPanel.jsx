import React, { useState, useEffect } from 'react';
import MetricsCard from './MetricsCard.jsx';
import { fetchSimilarityStats } from '../../api/client.js';
import './SimilarityPanel.css';

export default function SimilarityPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadStats = async () => {
    try {
      const result = await fetchSimilarityStats();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load similarity stats');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const getMaxCount = () => {
    if (!data || !data.distribution) return 1;
    return Math.max(...Object.values(data.distribution));
  };

  const maxCount = getMaxCount();

  return (
    <MetricsCard title="Chunk Similarity" loading={loading} error={error}>
      {data && (
        <>
          <div className="metric-row">
            <span className="metric-label">Avg Top Score</span>
            <span className="metric-value score-good">
              {data.statistics.avg_top_score.toFixed(3)}
            </span>
          </div>

          <div className="metric-row">
            <span className="metric-label">Out of Scope</span>
            <span className={`metric-value ${data.statistics.out_of_scope_percentage > 20 ? 'score-danger' : 'score-good'}`}>
              {data.statistics.out_of_scope_percentage.toFixed(1)}%
            </span>
          </div>

          <div className="section-divider">Distribution</div>

          <div className="distribution-chart">
            {Object.entries(data.distribution).reverse().map(([range, count]) => {
              const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;
              return (
                <div key={range} className="distribution-bar">
                  <span className="bar-label">{range}</span>
                  <div className="bar-container">
                    <div
                      className="bar-fill"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className="bar-count">{count}</span>
                </div>
              );
            })}
          </div>

          <div className="thresholds-note">
            Out-of-scope threshold: {data.thresholds.out_of_scope_threshold} • Top-K: {data.thresholds.top_k}
          </div>

        </>
      )}
    </MetricsCard>
  );
}
