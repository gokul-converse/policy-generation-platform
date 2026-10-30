'use client';

import React, { useCallback } from 'react';
import { useStudio } from '../context';

// Mock JSON schema derived from the policy skills — mirrors the reference HTML's J() function
const MOCK_SCHEMA = {
  title: 'Leave request',
  fields: [
    { type: 'select', label: 'Leave type', options: ['Annual leave', 'Sick leave', 'Unpaid leave'] },
    { type: 'date', label: 'From' },
    { type: 'date', label: 'To' },
    { type: 'textarea', label: 'Reason (optional)' },
  ],
  actions: [{ label: 'Submit request' }],
};

// Inline renderer — mirrors the reference HTML's renderer() function
const PolicyFormRenderer: React.FC<{ skills: { rule: string }[] }> = ({ skills }) => (
  <div className="form">
    <h3>{MOCK_SCHEMA.title}</h3>
    <div className="mono" style={{ color: 'var(--mu)' }}>
      Governed by {skills.length} policy rules
    </div>

    {MOCK_SCHEMA.fields.map((f) => (
      <div className="fld" key={f.label}>
        <label>{f.label}</label>
        {f.type === 'select' ? (
          <select>
            {(f.options ?? []).map((o) => (
              <option key={o}>{o}</option>
            ))}
          </select>
        ) : f.type === 'textarea' ? (
          <textarea rows={3} />
        ) : (
          <input type="date" />
        )}
      </div>
    ))}

    <div className="note">
      {skills.map((k, i) => (
        <React.Fragment key={i}>
          {k.rule}
          {i < skills.length - 1 && <br />}
        </React.Fragment>
      ))}
    </div>

    <div style={{ marginTop: '20px' }}>
      {MOCK_SCHEMA.actions.map((a) => (
        <button
          key={a.label}
          className="btn p"
          onClick={() => {}}
          type="button"
        >
          {a.label}
        </button>
      ))}
    </div>
  </div>
);

export const Screen4Preview: React.FC = () => {
  const {
    skills,
    previewTab,
    isPreviewLoading,
    setPreviewTab,
    goBack,
    handleSaveAndGoToPolicies,
    showToast,
  } = useStudio();

  const schemaWithRules = {
    ...MOCK_SCHEMA,
    rules: skills.map((k) => k.rule),
  };

  const onSubmitDemo = useCallback(() => {
    showToast('Demo only – no request sent');
  }, [showToast]);

  if (isPreviewLoading) {
    return (
      <div>
        <div className="load">
          <div className="spin" />
          <div>Generating the interface from your policy…</div>
          <span className="mono">POST /api/master-policy/render</span>
        </div>
        {/* No footer during loading */}
      </div>
    );
  }

  return (
    <div>
      {/* Header row with title and segmented control */}
      <div className="row sp" style={{ marginBottom: '20px' }}>
        <div>
          <h1>Preview</h1>
          <p className="sub" style={{ margin: 0 }}>
            Rendered from the JSON returned by the cloud model.
          </p>
        </div>
        <div className="seg">
          <button
            className={previewTab === 'ui' ? 'on' : ''}
            onClick={() => setPreviewTab('ui')}
          >
            Interface
          </button>
          <button
            className={previewTab === 'js' ? 'on' : ''}
            onClick={() => setPreviewTab('js')}
          >
            JSON
          </button>
        </div>
      </div>

      {/* Content card */}
      <div className="card">
        {previewTab === 'js' ? (
          <pre className="json">{JSON.stringify(schemaWithRules, null, 2)}</pre>
        ) : (
          <PolicyFormRenderer skills={skills} />
        )}
      </div>

      {/* Sticky footer */}
      <div className="foot">
        <button className="btn" onClick={goBack}>
          Edit policy
        </button>
        <button className="btn p" onClick={handleSaveAndGoToPolicies}>
          Save and go to policies
        </button>
      </div>
    </div>
  );
};
