/**
 * JSON Playground
 * Live JSON editor with real-time UI rendering
 */

'use client';

import React from 'react';
import { JSONUIRenderer } from '@/lib/ui-renderer';
import { validateUISchema, getErrorSummary } from '@/lib/ui-renderer/utils';
import { UISchema } from '@/types/ui-schema';

// Import examples for quick loading
import fullAppExampleJson from '@/lib/ui-renderer/examples/full-app-example.json';
import dashboardExampleJson from '@/lib/ui-renderer/examples/dashboard-example.json';
import formExampleJson from '@/lib/ui-renderer/examples/form-example.json';
import interactiveExampleJson from '@/lib/ui-renderer/examples/interactive-example.json';

const fullAppExample = fullAppExampleJson as UISchema;
const dashboardExample = dashboardExampleJson as UISchema;
const formExample = formExampleJson as UISchema;
const interactiveExample = interactiveExampleJson as UISchema;

const examples = {
  fullApp: fullAppExample,
  dashboard: dashboardExample,
  form: formExample,
  interactive: interactiveExample,
};

// Simple starter template
const starterTemplate: UISchema = {
  version: '1.0',
  metadata: {
    title: 'Starter Template',
    description: 'Simple starting point',
  },
  components: [
    {
      type: 'container',
      props: {
        maxWidth: 'lg',
        centered: true,
        padding: 8,
      },
      children: [
        {
          type: 'stack',
          props: {
            direction: 'vertical',
            gap: 4,
          },
          children: [
            {
              type: 'heading',
              props: {
                content: 'Welcome to JSON UI',
                level: 1,
              },
            },
            {
              type: 'text',
              props: {
                content: 'Edit the JSON on the left to see changes here in real-time.',
              },
            },
            {
              type: 'button',
              props: {
                label: 'Click Me',
                variant: 'primary',
              },
            },
          ],
        },
      ],
    },
  ],
};

export default function JSONPlaygroundPage() {
  const [jsonInput, setJsonInput] = React.useState(JSON.stringify(starterTemplate, null, 2));
  const [schema, setSchema] = React.useState<UISchema | null>(starterTemplate);
  const [error, setError] = React.useState<string | null>(null);
  const [layout, setLayout] = React.useState<'split' | 'editor' | 'preview'>('split');

  // Parse and validate JSON
  const parseJson = React.useCallback((input: string) => {
    try {
      const parsed = JSON.parse(input);
      const validation = validateUISchema(parsed);

      if (!validation.valid) {
        setError(getErrorSummary(validation));
        setSchema(null);
      } else {
        setError(null);
        setSchema(parsed);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid JSON');
      setSchema(null);
    }
  }, []);

  // Load example
  const loadExample = (exampleName: keyof typeof examples) => {
    const example = examples[exampleName];
    const jsonStr = JSON.stringify(example, null, 2);
    setJsonInput(jsonStr);
    parseJson(jsonStr);
  };

  // Handle JSON input change
  const handleJsonChange = (value: string) => {
    setJsonInput(value);
    parseJson(value);
  };

  // Format JSON
  const formatJson = () => {
    try {
      const parsed = JSON.parse(jsonInput);
      const formatted = JSON.stringify(parsed, null, 2);
      setJsonInput(formatted);
    } catch {
      // Keep as is if invalid
    }
  };

  // Clear editor
  const clearEditor = () => {
    const empty = JSON.stringify(starterTemplate, null, 2);
    setJsonInput(empty);
    parseJson(empty);
  };

  return (
        <div style={{ minHeight: 'calc(100vh - 56px)', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>

            {/* Toolbar */}
                <div style={{
                  background: 'var(--sf)',
                  borderBottom: '1px solid var(--ln)',
                  padding: '10px 24px',
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                }}>
                  {/* Example loaders */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--mu)' }}>Load example:</span>
                    {(['fullApp', 'dashboard', 'form', 'interactive'] as const).map((ex) => (
                      <button key={ex} className="btn" style={{ height: '32px', fontSize: '13px' }} onClick={() => loadExample(ex)}>
                        {ex === 'fullApp' ? 'Full App' : ex.charAt(0).toUpperCase() + ex.slice(1)}
                      </button>
                    ))}
                  </div>

                      {/* Actions + layout switcher */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button className="ghost" style={{ margin: 0, fontSize: '13px' }} onClick={formatJson}>Format</button>
                        <button className="ghost" style={{ margin: 0, fontSize: '13px' }} onClick={clearEditor}>Reset</button>
                        <div style={{ width: '1px', height: '20px', background: 'var(--ln)', margin: '0 4px' }} />
                        <div className="seg">
                          {(['split', 'editor', 'preview'] as const).map((v) => (
                <button
                  key={v}
                  className={layout === v ? 'on' : ''}
                  onClick={() => setLayout(v)}
                  style={{ textTransform: 'capitalize' }}
                >
                  {v}
                </button>
              ))}
                      </div>
                    </div>
                  </div>

                    {/* Main content: editor + preview */}
                    <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: '500px' }}>

                      {/* JSON Editor pane */}
                      {(layout === 'split' || layout === 'editor') && (
                            <div style={{
                              width: layout === 'split' ? '50%' : '100%',
                              display: 'flex',
                              flexDirection: 'column',
                              borderRight: layout === 'split' ? '1px solid var(--ln)' : 'none',
                            }}>
                              {/* Pane header */}
                              <div style={{
                                background: 'var(--sf)',
                                borderBottom: '1px solid var(--ln)',
                                padding: '8px 16px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                              }}>
                                <span className="eyebrow" style={{ margin: 0 }}>JSON Schema</span>
                                <span className="mono" style={{ color: 'var(--mu)' }}>
                                  {jsonInput.split('\n').length} lines · {jsonInput.length} chars
                                </span>
                              </div>

                                {/* Editor textarea */}
                                <div style={{ flex: 1, position: 'relative' }}>
                                  <textarea
                                    value={jsonInput}
                                    onChange={(e) => handleJsonChange(e.target.value)}
                                    spellCheck={false}
                                    placeholder="Enter JSON schema here…"
                                    style={{
                                      position: 'absolute',
                                      inset: 0,
                                      width: '100%',
                                      height: '100%',
                                      padding: '16px',
                                      fontFamily: 'var(--mono)',
                                      fontSize: '13px',
                                      lineHeight: 1.6,
                                      background: '#FDFCFB',
                                      color: 'var(--ink)',
                                      border: 0,
                                      outline: 0,
                                      resize: 'none',
                                    }}
                                  />
                                </div>

                                {/* Error banner */}
                                {error && (
                                      <div style={{
                                        borderTop: '1px solid #F1C4C4',
                                        background: '#FEF3F3',
                                        padding: '10px 16px',
                                      }}>
                                        <p className="mono" style={{ color: '#B4280F', margin: 0, whiteSpace: 'pre-wrap', fontSize: '12px' }}>
                                          {error}
                                        </p>
                                      </div>
              )}
                                  </div>
                                )}

                                {/* Live Preview pane */}
                                {(layout === 'split' || layout === 'preview') && (
                                      <div style={{
                                        width: layout === 'split' ? '50%' : '100%',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        background: 'var(--bg)',
                                      }}>
                                        {/* Pane header */}
                                        <div style={{
                                          background: 'var(--sf)',
                                          borderBottom: '1px solid var(--ln)',
                                          padding: '8px 16px',
                                          display: 'flex',
                                          alignItems: 'center',
                                          justifyContent: 'space-between',
                                        }}>
                                          <span className="eyebrow" style={{ margin: 0 }}>Live Preview</span>
                                          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: error ? '#B4280F' : 'var(--ac)', fontWeight: 500 }}>
                                            <span style={{
                                              width: '7px', height: '7px', borderRadius: '50%',
                                              background: error ? '#B4280F' : '#3BA17F',
                                              display: 'inline-block',
                                            }} />
                                            {error ? 'Invalid' : 'Valid'}
                                          </span>
                                        </div>

                                          {/* Preview content */}
                                          <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
                                            {schema ? (
                                              <JSONUIRenderer schema={schema} debug={false} />
                                            ) : (
                                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                                                    <div className="empty" style={{ maxWidth: '280px' }}>
                                                      <div style={{ marginBottom: '8px', color: 'var(--ln)' }}>
                                                        <svg width="36" height="36" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ margin: '0 auto', display: 'block' }}>
                                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                                                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                                        </svg>
                                                      </div>
                                                      <div style={{ fontWeight: 500, color: 'var(--ink)', marginBottom: '4px' }}>
                                                        {error ? 'Invalid JSON' : 'No preview'}
                                                      </div>
                                                      <div>
                                                        {error ? 'Fix the errors on the left to see the preview.' : 'Enter a valid JSON schema to render the preview.'}
                                                      </div>
                                                    </div>
                                                  </div>
                )}
                                                </div>
                                              </div>
                                            )}
                                          </div>

                                            {/* Status bar */}
                                            <div style={{
                                              background: 'var(--sf)',
                                              borderTop: '1px solid var(--ln)',
                                              padding: '7px 24px',
                                              display: 'flex',
                                              alignItems: 'center',
                                              justifyContent: 'space-between',
                                            }}>
                                              <span className="mono" style={{ color: 'var(--mu)' }}>
                                                JSON UI Playground
                                              </span>
                                              <span className="mono" style={{ color: 'var(--mu)' }}>
                                                Tip: Format tidies the JSON · Reset restores the starter template
                                              </span>
                                            </div>

                                          </div>
                                        </div>
                                        );
}
