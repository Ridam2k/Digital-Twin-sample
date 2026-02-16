import React from 'react';
import Header from '../components/Header/Header.jsx';
import AvatarPanel from '../components/Avatar/AvatarPanel.jsx';
import ConvPanel from '../components/Conversation/ConvPanel.jsx';
import ModeToast from '../components/Toast/ModeToast.jsx';

export default function ChatPage({ messages, mode, systemStatus, routerScores, showModeToast, onQuery }) {
  return (
    <div className="app-container">
      <Header mode={mode} systemStatus={systemStatus} showNav={true} />
      <AvatarPanel systemStatus={systemStatus} />
      <ConvPanel
        messages={messages}
        onSubmit={onQuery}
        disabled={systemStatus === 'processing'}
      />
      {showModeToast && (
        <ModeToast mode={mode} routerScores={routerScores} />
      )}
    </div>
  );
}
