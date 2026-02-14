import React, { useState, useEffect, useRef } from 'react';
import { Mic, ArrowRight } from 'lucide-react';
import './ConvPanel.css';

export default function ConvPanel({ messages, onSubmit, disabled }) {
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = () => {
    const trimmed = inputText.trim();
    if (trimmed !== '' && !disabled) {
      onSubmit(trimmed);
      setInputText('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="conv-panel">
      <div className="transcript-feed">
        {messages.map((msg) => (
          <div key={msg.id} className={`message message-${msg.role}`}>
            {msg.role === 'user' ? (
              <>
                <div className="message-label">YOU ›</div>
                <div className="message-text">{msg.text}</div>
              </>
            ) : (
              <>
                <div className={`message-text twin-text ${msg.outOfScope ? 'oos-text' : ''}`}>
                  {msg.outOfScope && '⊘ '}
                  {msg.text}
                </div>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="citations-row">
                    {msg.citations.map((cite) => (
                      <button key={cite.index} className="citation-badge">
                        [{cite.index}] {cite.doc_title} · {cite.score.toFixed(2)}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-dock">
        <button
          className={`voice-button ${isRecording ? 'recording' : ''}`}
          onClick={() => setIsRecording(!isRecording)}
          disabled={disabled}
        >
          <Mic size={18} />
        </button>

        <textarea
          className="text-input"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Processing..." : "Ask anything. Technical or personal."}
          rows={1}
          disabled={disabled}
        />

        <button
          className="submit-button"
          onClick={handleSubmit}
          disabled={disabled || inputText.trim() === ''}
        >
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}
