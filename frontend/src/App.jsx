import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatPage from './pages/ChatPage.jsx';
import ObservabilityPage from './pages/ObservabilityPage.jsx';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/observability" element={<ObservabilityPage />} />
      </Routes>
    </BrowserRouter>
  );
}
