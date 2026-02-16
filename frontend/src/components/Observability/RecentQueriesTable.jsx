import React from 'react';
import './RecentQueriesTable.css';

export default function RecentQueriesTable({ entries }) {
  if (!entries || entries.length === 0) {
    return <div className="no-queries">No queries logged yet</div>;
  }

  const getScoreClass = (score) => {
    if (score >= 0.8) return 'score-good';
    if (score >= 0.5) return 'score-warning';
    return 'score-danger';
  };

  return (
    <div className="recent-queries-table">
      <h4 className="table-title">Recent Queries (Last 5)</h4>
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Query</th>
            <th>Namespace</th>
            <th>Groundedness</th>
            <th>Persona</th>
            <th>Fabricated</th>
          </tr>
        </thead>
        <tbody>
          {entries.slice(0, 5).map((entry, idx) => (
            <tr key={idx}>
              <td className="timestamp">
                {new Date(entry.ts).toLocaleString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </td>
              <td className="query-text" title={entry.query}>
                {entry.query.length > 50
                  ? entry.query.substring(0, 50) + '...'
                  : entry.query}
              </td>
              <td className="namespace">{entry.namespace}</td>
              <td className={`score ${getScoreClass(entry.groundedness_score)}`}>
                {entry.groundedness_score.toFixed(3)}
              </td>
              <td className={`score ${getScoreClass(entry.persona_consistency_score)}`}>
                {entry.persona_consistency_score.toFixed(3)}
              </td>
              <td className="fabricated">
                {Array.isArray(entry.fabricated_claims) ? entry.fabricated_claims.length : 0}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
