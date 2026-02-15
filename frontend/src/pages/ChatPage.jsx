import React, { useState, useEffect, useRef } from 'react';
import Header from '../components/Header/Header.jsx';
import AvatarPanel from '../components/Avatar/AvatarPanel.jsx';
import ConvPanel from '../components/Conversation/ConvPanel.jsx';
import ModeToast from '../components/Toast/ModeToast.jsx';
import { sendQuery, APIError } from '../api/client.js';

export default function ChatPage() {
  // State management
  const [mode, setMode] = useState('technical');
  const [systemStatus, setSystemStatus] = useState('idle');
  const [routerScores, setRouterScores] = useState({
    technical: 0.0,
    nontechnical: 0.0,
  });
  const [messages, setMessages] = useState([]);
  const [showModeToast, setShowModeToast] = useState(false);

  const nextMessageId = useRef(1);

  // Handler for new queries from ConvPanel
  const handleQuery = async (queryText) => {
    // 1. Add user message immediately
    const userMsg = {
      id: nextMessageId.current++,
      role: 'user',
      text: queryText,
    };
    setMessages((prev) => [...prev, userMsg]);

    // 2. Set processing state
    setSystemStatus('processing');

    try {
      // 3. Call API
      const result = await sendQuery(queryText);

      // 4. Update mode + scores if changed
      if (result.mode !== mode) {
        setMode(result.mode);
        setRouterScores(result.router_scores);
        setShowModeToast(true);
      }

      // 5. Set speaking state briefly (simulate TTS delay)
      setSystemStatus('speaking');

      // 6. Add assistant message
      const assistantMsg = {
        id: nextMessageId.current++,
        role: 'twin',
        text: result.response,
        citations: result.citations,
        outOfScope: result.out_of_scope,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // 7. Return to idle after "speaking"
      setTimeout(() => {
        setSystemStatus(result.out_of_scope ? 'out-of-scope' : 'idle');
      }, 800);

    } catch (error) {
      // 8. Error handling
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

  // Hide toast after timeout
  useEffect(() => {
    if (showModeToast) {
      const timer = setTimeout(() => setShowModeToast(false), 2500);
      return () => clearTimeout(timer);
    }
  }, [showModeToast]);

  return (
    <div className="app-container">
      <Header mode={mode} systemStatus={systemStatus} showNav={true} />
      <AvatarPanel systemStatus={systemStatus} />
      <ConvPanel
        messages={messages}
        onSubmit={handleQuery}
        disabled={systemStatus === 'processing'}
      />
      {showModeToast && (
        <ModeToast mode={mode} routerScores={routerScores} />
      )}
    </div>
  );
}
