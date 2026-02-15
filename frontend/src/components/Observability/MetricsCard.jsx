import React from 'react';
import './MetricsCard.css';

export default function MetricsCard({ title, children, loading = false, error = null }) {
  return (
    <div className="metrics-card">
      <h3 className="card-title">{title}</h3>
      <div className="card-content">
        {loading ? (
          <div className="loading-skeleton">
            <div className="skeleton-line" />
            <div className="skeleton-line" />
            <div className="skeleton-line" />
          </div>
        ) : error ? (
          <div className="error-message">{error}</div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
