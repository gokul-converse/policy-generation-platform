'use client';

import React, { useRef, useState, useCallback } from 'react';
import { useStudio } from '../context';

const TOPICS = ['Eligibility', 'Accrual', 'Carry-over', 'Approval'];

export const Screen2Skills: React.FC = () => {
  const {
    requirementId,
    skills,
    highlightedSkillId,
    isCreatingSkill,
    handleCreateSkill,
    handleGeneratePolicy,
    openSkillDrawer,
  } = useStudio();

  const ruleRef = useRef<HTMLTextAreaElement>(null);
  const [ruleValue, setRuleValue] = useState(
    'Staff accrue 1.5 days of paid leave per month after probation.'
  );

  const onCreateSkill = useCallback(async () => {
    const val = ruleRef.current?.value.trim() ?? ruleValue.trim();
    if (!val || isCreatingSkill) return;
    await handleCreateSkill(val);
    setRuleValue('');
    if (ruleRef.current) ruleRef.current.value = '';
  }, [ruleValue, isCreatingSkill, handleCreateSkill]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        onCreateSkill();
      }
    },
    [onCreateSkill]
  );

  return (
    <div>
      <h1>Create skills</h1>
      <p className="sub">
        Each skill is one rule of the policy. Add the rules you need, then generate the policy.
      </p>

      <div className="cols">
        {/* Left column */}
        <div>
          <p className="eyebrow">Topics from your requirements</p>
          <ul className="topics">
            {TOPICS.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>

          <div className="card cmd">
            <textarea
              ref={ruleRef}
              aria-label="Rule for the new skill"
              placeholder="Describe a rule, e.g. Unused leave carries over up to 5 days."
              defaultValue={ruleValue}
              onChange={(e) => setRuleValue(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={isCreatingSkill}
            />
            <div className="bar">
              <span className="chip">POST /api/skills</span>
              <button
                className="btn p"
                onClick={onCreateSkill}
                disabled={isCreatingSkill}
              >
                {isCreatingSkill ? 'Creating…' : 'Create skill'}
              </button>
            </div>
          </div>
        </div>

        {/* Right column */}
        <div>
          <p className="eyebrow">Generated skills · {skills.length}</p>
          <div className="card">
            {/* Loading shimmer when creating */}
            {isCreatingSkill && (
              <div className="sk">
                <div className="shim" style={{ width: '50%' }} />
                <div className="shim" />
              </div>
            )}

            {/* Skills list */}
            {skills.length > 0 || isCreatingSkill ? (
              skills.map((k) => (
                <div
                  key={k.id}
                  className={`sk${highlightedSkillId === k.id ? ' hl' : ''}`}
                >
                  <div className="t">
                    <span>{k.name}</span>
                    <span className="tag g mono">v{k.ver}</span>
                  </div>
                  <p>{k.rule}</p>
                  <button
                    className="lnk"
                    onClick={() => openSkillDrawer(k.id)}
                  >
                    Preview skill
                  </button>
                </div>
              ))
            ) : (
              <div className="empty">Skills you create appear here.</div>
            )}
          </div>
        </div>
      </div>

      {/* Sticky footer */}
      <div className="foot">
        <span className="mono" style={{ color: 'var(--mu)' }}>
          {requirementId}
        </span>
        <button
          className="btn p"
          onClick={handleGeneratePolicy}
          disabled={!skills.length}
        >
          Generate policy
        </button>
      </div>
    </div>
  );
};
