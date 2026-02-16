import React, { useState, useEffect, useRef } from 'react';
import { Mic, ArrowRight } from 'lucide-react';
import { ingestGoogleDrive, ingestGithub } from '../../api/client.js';
import './ConvPanel.css';

export default function ConvPanel({ messages, onSubmit, disabled }) {
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isIngestingGDrive, setIsIngestingGDrive] = useState(false);
  const [isIngestingGithub, setIsIngestingGithub] = useState(false);
  const [ingestError, setIngestError] = useState(null);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const textareaRef = useRef(null);
  const baseTextRef = useRef('');
  const [speechSupported, setSpeechSupported] = useState(false);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initialize SpeechRecognition once on mount
  useEffect(() => {
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) return;

    setSpeechSupported(true);

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      let interim = '';
      let final = '';
      for (let i = 0; i < event.results.length; i++) {
        const text = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += text;
        } else {
          interim += text;
        }
      }

      const base = baseTextRef.current;
      const separator = base.trim() ? ' ' : '';

      if (final) {
        const newText = base + separator + final.trim();
        baseTextRef.current = newText;
        setInputText(newText);
      } else if (interim) {
        setInputText(base + separator + interim);
      }
    };

    recognition.onerror = (event) => {
      if (event.error !== 'aborted') {
        console.warn('Speech recognition error:', event.error);
      }
      setIsRecording(false);
    };

    recognition.onend = () => {
      setIsRecording(false);
      textareaRef.current?.focus();
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.abort();
    };
  }, []);

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

  const toggleRecording = async () => {
    if (!recognitionRef.current) return;
    if (isRecording) {
      recognitionRef.current.stop();
    } else {
      // Request mic permission explicitly before starting recognition
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((t) => t.stop());
      } catch (err) {
        console.warn('Microphone permission denied:', err);
        return;
      }
      baseTextRef.current = inputText;
      try {
        recognitionRef.current.start();
        setIsRecording(true);
      } catch (err) {
        console.warn('Failed to start speech recognition:', err);
      }
    }
  };

  const handleGDriveIngest = async () => {
    setIsIngestingGDrive(true);
    setIngestError(null);
    try {
      const result = await ingestGoogleDrive();
      console.log('Google Drive ingestion complete:', result);
    } catch (error) {
      console.error('Google Drive ingestion failed:', error);
      setIngestError(error.message || 'Google Drive ingestion failed');
    } finally {
      setIsIngestingGDrive(false);
    }
  };

  const handleGithubIngest = async () => {
    setIsIngestingGithub(true);
    setIngestError(null);
    try {
      const result = await ingestGithub();
      console.log('GitHub ingestion complete:', result);
    } catch (error) {
      console.error('GitHub ingestion failed:', error);
      setIngestError(error.message || 'GitHub ingestion failed');
    } finally {
      setIsIngestingGithub(false);
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

      <div className="ingestion-dock">
        <button
          className="ingest-button"
          onClick={handleGDriveIngest}
          disabled={isIngestingGDrive || isIngestingGithub || disabled}
        >
          {isIngestingGDrive ? 'Ingesting Google Drive...' : 'Ingest Google Drive'}
        </button>

        <button
          className="ingest-button"
          onClick={handleGithubIngest}
          disabled={isIngestingGDrive || isIngestingGithub || disabled}
        >
          {isIngestingGithub ? 'Ingesting Github...' : 'Ingest Github'}
        </button>

        {ingestError && (
          <div className="ingest-error">{ingestError}</div>
        )}
      </div>

      <div className="input-dock">
        {speechSupported && (
          <button
            className={`voice-button ${isRecording ? 'recording' : ''}`}
            onClick={toggleRecording}
            disabled={disabled}
            title={isRecording ? 'Stop recording' : 'Start voice input'}
          >
            <Mic size={18} />
          </button>
        )}

        <textarea
          ref={textareaRef}
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
