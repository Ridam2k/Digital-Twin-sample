import React, { useState, useRef, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatPage from './pages/ChatPage.jsx';
import ObservabilityPage from './pages/ObservabilityPage.jsx';
import { sendQuery, streamQuery, APIError } from './api/client.js';
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

  const handleQuery = async (queryText, contentType = null) => {
    const userMsg = {
      id: nextMessageId.current++,
      role: 'user',
      text: queryText,
    };
    setMessages((prev) => [...prev, userMsg]);
    setSystemStatus('processing');

    try {
      // Using streaming client for progressive response delivery
      await streamQuery(queryText, contentType, {
        onResponse: (data) => {
          // Immediately display response when it arrives
          if (data.mode !== mode) {
            setMode(data.mode);
            setRouterScores(data.router_scores);
            setShowModeToast(true);
          }

          setSystemStatus('speaking');

          const assistantMsg = {
            id: nextMessageId.current++,
            role: 'twin',
            text: data.response,
            citations: data.citations,
            outOfScope: data.out_of_scope,
          };

          setMessages((prev) => [...prev, assistantMsg]);

          setTimeout(() => {
            setSystemStatus(data.out_of_scope ? 'out-of-scope' : 'idle');
          }, 800);
        },

        onMetrics: (data) => {
          // Metrics are logged server-side, just log to console for debugging
          console.log('Metrics computed:', data);
        },

        onDone: () => {
          console.log('Query stream completed');
        },

        onError: (error) => {
          console.error('Query stream error:', error);
          throw error; // Let outer catch handle it
        }
      });

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
