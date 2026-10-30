'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useStudio } from './context';
import { STEP_NAMES } from './mock-data';

const slug = (name: string) =>
  name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');

export const StudioShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname();
  const {
    screen,
    requirementId,
    toastMessage,
    drawerSkillId,
    skills,
    goBack,
    goHome,
    closeSkillDrawer,
  } = useStudio();

  const isPlayground = pathname === '/json-playground';
  const isScreen1 = screen === 1 && !isPlayground;
  const drawerSkill = drawerSkillId ? skills.find((k) => k.id === drawerSkillId) : null;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && drawerSkillId) {
        closeSkillDrawer();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [drawerSkillId, closeSkillDrawer]);

  const skillMarkdown = drawerSkill
    ? `---
name: ${slug(drawerSkill.name)}
description: ${drawerSkill.rule}
version: ${drawerSkill.ver}
requirement: ${requirementId}
---

# ${drawerSkill.name}

## Rule
${drawerSkill.rule}

## Applies to
All covered employees.
`
    : '';

  return (
    <>
      {/* Header / Navbar */}
      <header className="studio-header">
        <div className="row" style={{ gap: '16px' }}>
          <button
            className="brand"
            onClick={goHome}
            aria-label="Policy Studio home"
          >
            <span className="dot" />
            Policy Studio
          </button>
          {!isScreen1 && (
            <button
              className="ghost"
              onClick={goBack}
              style={{
                margin: 0,
                fontSize: '14px',
                color: 'var(--ink)',
                border: '1px solid var(--ln)',
                background: 'var(--sf)',
              }}
            >
              ← Back
            </button>
          )}
        </div>

        <div className="row" style={{ gap: '16px' }}>
          {isPlayground ? (
            <Link
              href="/"
              className="ghost"
              style={{
                fontSize: '13px',
                fontWeight: 500,
                color: 'var(--ac)',
                textDecoration: 'none',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              Policy Studio
            </Link>
          ) : (
            <Link
              href="/json-playground"
              className="ghost"
              style={{
                fontSize: '13px',
                fontWeight: 500,
                color: 'var(--ac)',
                textDecoration: 'none',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              JSON Playground
            </Link>
          )}

          <div className="crumb">
            {isPlayground ? (
              <b>JSON Playground</b>
            ) : (
              <>
                <b>{STEP_NAMES[screen]}</b>
                {screen > 1 && screen < 5 && (
                  <span className="mono">{requirementId}</span>
                )}
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className={`studio-main ${isScreen1 || isPlayground ? 'wide' : ''}`}>
        {children}
      </main>

      {/* Toast Notification */}
      <div id="toast" role="status" className={toastMessage ? 'on' : ''}>
        {toastMessage}
      </div>

      {/* Skill Preview Drawer */}
      {drawerSkill && (
        <div id="drawer">
          <div
            className="scrim"
            onClick={closeSkillDrawer}
            aria-label="Close skill preview"
          />
          <aside className="panel" role="dialog" aria-label="Skill file preview">
            <div className="ph">
              <div>
                <div className="mono" style={{ fontSize: '13px', fontWeight: 500 }}>
                  {slug(drawerSkill.name)}.md
                </div>
                <div style={{ fontSize: '12.5px', color: 'var(--mu)' }}>
                  Skill file · v{drawerSkill.ver}
                </div>
              </div>
              <button
                className="ghost"
                style={{ margin: 0 }}
                onClick={closeSkillDrawer}
                aria-label="Close preview"
              >
                Close
              </button>
            </div>
            <div className="pb">
              <pre>{skillMarkdown}</pre>
            </div>
          </aside>
        </div>
      )}
    </>
  );
};
