import React from 'react';
import Header from '../components/Header/Header.jsx';
import QualityPanel from '../components/Observability/QualityPanel.jsx';
import RetrievalPanel from '../components/Observability/RetrievalPanel.jsx';
import DatabasePanel from '../components/Observability/DatabasePanel.jsx';
import SimilarityPanel from '../components/Observability/SimilarityPanel.jsx';
import './ObservabilityPage.css';

export default function ObservabilityPage() {
  return (
    <div className="observability-container">
      <Header showNav={true} />
      <div className="observability-content">
        <h1 className="page-title">OBSERVABILITY DASHBOARD</h1>
        <div className="dashboard-grid">
          <QualityPanel />
          <RetrievalPanel />
          <DatabasePanel />
          <SimilarityPanel />
        </div>
      </div>
    </div>
  );
}
