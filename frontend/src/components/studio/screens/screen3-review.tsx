'use client';

import React, { useRef, useState, useCallback } from 'react';
import { useStudio } from '../context';

export const Screen3Review: React.FC = () => {
  const {
    requirementId,
    skills,
    sections,
    selectedSectionId,
    highlightedSkillId,
    handleSelectSection,
    handlePickSkillForSection,
    handleRegenerateSection,
    handleFinalizeMasterPolicy,
    openSkillDrawer,
  } = useStudio();

  const modRef = useRef<HTMLTextAreaElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const selectedSection = sections.find((s) => s.sectionId === selectedSectionId) ?? null;
  const appliedSkill =
    selectedSection?.appliedSkillId
      ? skills.find((k) => k.id === selectedSection.appliedSkillId) ?? null
      : null;

  const onModKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === '/') {
        const ta = e.currentTarget;
        if (!ta.value) {
          e.preventDefault();
          setMenuOpen(true);
        }
      } else if (e.key === 'Escape') {
        setMenuOpen(false);
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        onRegenerate();
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedSectionId]
  );

  const onRegenerate = useCallback(async () => {
    const instructions = modRef.current?.value.trim() ?? '';
    if (!selectedSectionId || !instructions) return;
    await handleRegenerateSection(instructions);
    if (modRef.current) modRef.current.value = '';
  }, [selectedSectionId, handleRegenerateSection]);

  const onPickSkill = useCallback(
    (skillId: string) => {
      handlePickSkillForSection(skillId);
      setMenuOpen(false);
      modRef.current?.focus();
    },
    [handlePickSkillForSection]
  );

  return (
    <div>
      <div className="cols">
        {/* Left: Document */}
        <div>
          <div className="card doc">
            <h2>Employee leave policy</h2>
            <span className="mono" style={{ color: 'var(--mu)' }}>
              Draft · {skills.length} skills
            </span>

            {sections.map((sec) => (
              <div key={sec.sectionId}>
                <h5>{sec.heading}</h5>
                <p
                  className={
                    highlightedSkillId && sec.appliedSkillId === highlightedSkillId
                      ? 'hl'
                      : selectedSectionId === sec.sectionId
                      ? 'hl'
                      : ''
                  }
                  onClick={() =>
                    handleSelectSection(
                      selectedSectionId === sec.sectionId ? null : sec.sectionId
                    )
                  }
                  title="Click to select and refine this section"
                >
                  {sec.paragraph}
                </p>
              </div>
            ))}
          </div>

          {/* Spacer then contextual editor (below document on left) */}
          <div style={{ height: '16px' }} />

          {/* Skill refinement composer */}
          <div className="card cmd" style={{ position: 'relative' }}>
            {/* Skill slash-picker menu */}
            {menuOpen && (
              <div className="menu">
                {skills.map((k) => (
                  <button key={k.id} onClick={() => onPickSkill(k.id)}>
                    <span className="mono">
                      /{k.name.toLowerCase().replace(/\s+/g, '-')}
                    </span>
                    <span className="tag g">v{k.ver}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Selected skill chip */}
            {appliedSkill && (
              <span className="chip" style={{ marginBottom: '6px', display: 'inline-flex' }}>
                /{appliedSkill.name.toLowerCase().replace(/\s+/g, '-')}
              </span>
            )}

            <textarea
              ref={modRef}
              aria-label="Refine a skill"
              placeholder={
                selectedSectionId
                  ? 'What should change in this section? (Type / to pick a skill)'
                  : 'Click a paragraph on the left to select it, then describe the change'
              }
              onKeyDown={onModKeyDown}
              disabled={!selectedSectionId}
            />
            <div className="bar">
              <span className="mono" style={{ color: 'var(--mu)' }}>
                PATCH /api/skills/:id
              </span>
              <button
                className="btn p"
                onClick={onRegenerate}
                disabled={!selectedSectionId}
              >
                Update skill
              </button>
            </div>
          </div>
        </div>

        {/* Right: Skills sidebar */}
        <div>
          <p className="eyebrow">Skills under {requirementId}</p>
          <div className="card">
            {skills.map((k) => (
              <div
                key={k.id}
                className={`sk${highlightedSkillId === k.id ? ' hl' : ''}`}
              >
                <div className="t">
                  <span>{k.name}</span>
                  <span className="tag g mono">v{k.ver}</span>
                </div>
                <p>{k.rule}</p>
                <button className="lnk" onClick={() => openSkillDrawer(k.id)}>
                  Preview skill
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sticky footer */}
      <div className="foot">
        <button
          className="btn"
          onClick={() => handleSelectSection(null)}
          style={{ visibility: selectedSectionId ? 'visible' : 'hidden' }}
        >
          Clear selection
        </button>
        <button className="btn p" onClick={handleFinalizeMasterPolicy}>
          Finalize master policy
        </button>
      </div>
    </div>
  );
};
