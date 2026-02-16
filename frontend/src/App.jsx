import React, { useState, useRef, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatPage from './pages/ChatPage.jsx';
import ObservabilityPage from './pages/ObservabilityPage.jsx';
import { sendQuery, APIError } from './api/client.js';
import './App.css';

export default function App() {
  const [mode, setMode] = useState('technical');
  const [systemStatus, setSystemStatus] = useState('idle');
  const [routerScores, setRouterScores] = useState({
    technical: 0.0,
    nontechnical: 0.0,
  });
  const [messages, setMessages] = useState([]);
  const [showModeToast, setShowModeToast] = useState(false);
  const nextMessageId = useRef(1);

  const handleQuery = async (queryText) => {
    const userMsg = {
      id: nextMessageId.current++,
      role: 'user',
      text: queryText,
    };
    setMessages((prev) => [...prev, userMsg]);
    setSystemStatus('processing');

    try {
      const result = await sendQuery(queryText);

      if (result.mode !== mode) {
        setMode(result.mode);
        setRouterScores(result.router_scores);
        setShowModeToast(true);
      }

      setSystemStatus('speaking');

      const assistantMsg = {
        id: nextMessageId.current++,
        role: 'twin',
        text: result.response,
        citations: result.citations,
        outOfScope: result.out_of_scope,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      setTimeout(() => {
        setSystemStatus(result.out_of_scope ? 'out-of-scope' : 'idle');
      }, 800);

    } catch (error) {
      console.error('Query failed:', error);
      const errorMsg = {
        id: nextMessageId.current++,
        role: 'twin',
        text: error instanceof APIError
          ? `Sorry, I encountered an error: ${error.detail}`
          : 'Sorry, something went wrong. Please try again.',
        citations: [],
        outOfScope: false,
      };
      setMessages((prev) => [...prev, errorMsg]);
      setSystemStatus('idle');
    }
  };

  useEffect(() => {
    if (showModeToast) {
      const timer = setTimeout(() => setShowModeToast(false), 2500);
      return () => clearTimeout(timer);
    }
  }, [showModeToast]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={
          <ChatPage
            messages={messages}
            mode={mode}
            systemStatus={systemStatus}
            routerScores={routerScores}
            showModeToast={showModeToast}
            onQuery={handleQuery}
          />
        } />
        <Route path="/observability" element={<ObservabilityPage />} />
      </Routes>
    </BrowserRouter>
  );
}
