import React, { useState, useEffect } from 'react';
import MetricsCard from './MetricsCard.jsx';
import { fetchDbStats } from '../../api/client.js';
import './DatabasePanel.css';

export default function DatabasePanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const result = await fetchDbStats();
        setData(result);
        setError(null);
      } catch (err) {
        setError(err.message || 'Failed to load database stats');
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, []);

  return (
    <MetricsCard title="Vector Database" loading={loading} error={error}>
      {data && (
        <>
          <div className="metric-row">
            <span className="metric-label">Total Chunks</span>
            <span className="metric-value-neutral">
              {data.total_chunks.toLocaleString()}
            </span>
          </div>

          <div className="metric-row">
            <span className="metric-label">Total Documents</span>
            <span className="metric-value-neutral">
              {data.total_documents.toLocaleString()}
            </span>
          </div>

          <div className="section-divider">By Namespace</div>

          {Object.entries(data.namespaces).map(([ns, stats]) => (
            <div key={ns} className="namespace-stats">
              <div className="namespace-header">{ns}</div>
              <div className="namespace-metrics">
                <div className="metric-row">
                  <span className="metric-label-small">Chunks</span>
                  <span className="metric-value-small-neutral">
                    {stats.chunk_count.toLocaleString()}
                  </span>
                </div>
                <div className="metric-row">
                  <span className="metric-label-small">Documents</span>
                  <span className="metric-value-small-neutral">
                    {stats.doc_count.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          ))}

          <div className="metadata-note">
            Collection: {data.collection_name} • Vector dim: {data.metadata.vector_dimension}
          </div>
        </>
      )}
    </MetricsCard>
  );
}
