'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useStudio } from '../context';
import { SUGGESTION_CHIPS } from '../mock-data';

export const Screen1Requirements: React.FC = () => {
  const {
    sidebarOpen,
    toggleSidebar,
    policies,
    messages,
    isFinalized,
    isBusy,
    handleNewPolicy,
    handleSendMessage,
    handleContinueToSkills,
    handleViewPolicy,
    handlePreviewPolicy,
    handleEditPolicy,
  } = useStudio();

  const [inputValue, setInputValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const isFirst = messages.length === 0;

  // Auto scroll to bottom of chat
  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages, isBusy]);

  const handleSubmit = async () => {
    if (!inputValue.trim() || isBusy) return;
    const text = inputValue;
    setInputValue('');
    await handleSendMessage(text);
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 50);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChipClick = (chipText: string) => {
    const formatted = `${chipText} for a 200-person company`;
    setInputValue(formatted);
    textareaRef.current?.focus();
  };

  return (
    <div className={`shell ${sidebarOpen ? '' : 'noside'}`}>
      {/* Sidebar */}
      <aside className="side" aria-label="Policies">
        <div className="row sp" style={{ marginBottom: '14px' }}>
          <span
            className="eyebrow"
            style={{ margin: 0, fontWeight: 600, color: 'var(--ink)' }}
          >
            Policies
          </span>
          <button
            className="ghost"
            style={{ margin: 0 }}
            onClick={toggleSidebar}
            aria-expanded={sidebarOpen}
          >
            Hide
          </button>
        </div>

        <button className="btn p" onClick={handleNewPolicy}>
          New policy
        </button>

        {policies.map((p) => (
          <div key={p.id} className="pi">
            <div className="pt">{p.title}</div>
            <div className="pm">
              {p.state} · {p.when}
            </div>
            <div className="pa">
              <button onClick={() => handleViewPolicy(p.id)}>View</button>
              <button onClick={() => handlePreviewPolicy(p.id)}>Preview</button>
              <button onClick={() => handleEditPolicy(p.id)}>Edit</button>
            </div>
          </div>
        ))}
      </aside>

      {/* Main Stage */}
      <section className="stage">
        {/* Stage Toolbar */}
        <div className="tools">
          {sidebarOpen ? (
            <span />
          ) : (
            <button
              className="btn tgl"
              onClick={toggleSidebar}
              aria-expanded={false}
            >
              Policies <span className="tag">{policies.length}</span>
            </button>
          )}
          <span className="status">
            <i />
            Connected
          </span>
        </div>

        {/* Content: Hero or Chat */}
        {isFirst ? (
          <div className="hero">
            <h1>What policy do we need?</h1>
            <p className="sub">
              Describe it in a sentence or two. The requirement agent asks for whatever is missing.
            </p>

            <div className="composer big">
              <textarea
                ref={textareaRef}
                rows={3}
                aria-label="Policy description"
                placeholder="e.g. A leave policy for a 200-person company, covering permanent and contract staff"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isBusy}
              />
              <button
                className="btn p"
                onClick={handleSubmit}
                disabled={isBusy || !inputValue.trim()}
              >
                Start
              </button>
            </div>

            <div className="ex">
              {SUGGESTION_CHIPS.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => handleChipClick(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="chat">
            <div className="msgs">
              {messages.map((m) => {
                if (m.role === 'user') {
                  return (
                    <div key={m.id} className="m u">
                      {m.text}
                    </div>
                  );
                }

                if (m.isDraft) {
                  return (
                    <div key={m.id} className="card draft">
                      <div className="row sp" style={{ marginBottom: '10px' }}>
                        <span className="eyebrow" style={{ margin: 0 }}>
                          Policy draft
                        </span>
                        <span className="tag">finalized: true</span>
                      </div>
                      <h3>Employee leave policy</h3>
                      <ul>
                        <li>Covers permanent and contract staff</li>
                        <li>1.5 days accrue monthly; up to 5 days carry over</li>
                        <li>Line manager approves; apply 5 days ahead</li>
                      </ul>
                    </div>
                  );
                }

                return (
                  <div key={m.id} className="m a">
                    <small>Requirement agent</small>
                    {m.text}
                  </div>
                );
              })}

              {isBusy && <div className="typing">Agent is typing…</div>}
              <div ref={messagesEndRef} id="msgs-end" />
            </div>

            {isFinalized ? (
              <div className="row" style={{ justifyContent: 'flex-end' }}>
                <button className="btn p" onClick={handleContinueToSkills}>
                  Continue to skills
                </button>
              </div>
            ) : (
              <div className="composer">
                <textarea
                  ref={textareaRef}
                  rows={1}
                  aria-label="Your response"
                  placeholder="Your answer"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isBusy}
                />
                <button
                  className="btn p"
                  onClick={handleSubmit}
                  disabled={isBusy || !inputValue.trim()}
                >
                  Send
                </button>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
};
