import React, { useState, useEffect } from 'react';
import MetricsCard from './MetricsCard.jsx';
import { fetchEvalMetrics } from '../../api/client.js';
import './QualityPanel.css';

export default function QualityPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadMetrics = async () => {
    try {
      const result = await fetchEvalMetrics();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to load metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();

    // Auto-refresh every 30 seconds
    const interval = setInterval(loadMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  const getScoreClass = (score) => {
    if (score >= 0.8) return 'score-good';
    if (score >= 0.5) return 'score-warning';
    return 'score-danger';
  };

  return (
    <MetricsCard title="Quality Metrics" loading={loading} error={error}>
      {data && (
        <>
          <div className="metric-row">
            <span className="metric-label">Avg Groundedness</span>
            <span className={`metric-value ${getScoreClass(data.summary.avg_groundedness_score)}`}>
              {data.summary.avg_groundedness_score.toFixed(3)}
            </span>
          </div>

          <div className="metric-row">
            <span className="metric-label">Avg Persona Consistency</span>
            <span className={`metric-value ${getScoreClass(data.summary.avg_persona_consistency_score)}`}>
              {data.summary.avg_persona_consistency_score.toFixed(3)}
            </span>
          </div>

          <div className="metric-row">
            <span className="metric-label">Fabricated Claims</span>
            <span className={`metric-value ${data.summary.total_fabricated_claims > 0 ? 'score-warning' : 'score-good'}`}>
              {data.summary.total_fabricated_claims}
            </span>
          </div>

          <div className="metric-row">
            <span className="metric-label">Total Queries</span>
            <span className="metric-value-neutral">
              {data.summary.total_queries}
            </span>
          </div>

          {Object.keys(data.by_namespace).length > 0 && (
            <>
              <div className="section-divider">By Namespace</div>
              {Object.entries(data.by_namespace).map(([ns, stats]) => (
                <div key={ns} className="namespace-stats">
                  <div className="namespace-header">{ns}</div>
                  <div className="namespace-metrics">
                    <div className="metric-row">
                      <span className="metric-label-small">Groundedness</span>
                      <span className={`metric-value-small ${getScoreClass(stats.avg_groundedness)}`}>
                        {stats.avg_groundedness.toFixed(3)}
                      </span>
                    </div>
                    <div className="metric-row">
                      <span className="metric-label-small">Persona</span>
                      <span className={`metric-value-small ${getScoreClass(stats.avg_persona)}`}>
                        {stats.avg_persona.toFixed(3)}
                      </span>
                    </div>
                    <div className="metric-row">
                      <span className="metric-label-small">Queries</span>
                      <span className="metric-value-small-neutral">{stats.count}</span>
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}

          <div className="refresh-note">Auto-refreshing every 30s</div>
        </>
      )}
    </MetricsCard>
  );
}
