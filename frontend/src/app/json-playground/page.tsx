/**
 * JSON Playground
 * Live JSON editor with real-time UI rendering
 */

'use client';

import React from 'react';
import { JSONUIRenderer } from '@/lib/ui-renderer';
import { validateUISchema, getErrorSummary } from '@/lib/ui-renderer/utils';
import { Navbar } from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
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
  const [showPreview, setShowPreview] = React.useState(true);
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      <Navbar title="JSON Playground" />

      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
          <div className="max-w-full mx-auto flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Load Example:</span>
              <Button size="sm" variant="outline" onClick={() => loadExample('fullApp')}>
                Full App
              </Button>
              <Button size="sm" variant="outline" onClick={() => loadExample('dashboard')}>
                Dashboard
              </Button>
              <Button size="sm" variant="outline" onClick={() => loadExample('form')}>
                Form
              </Button>
              <Button size="sm" variant="outline" onClick={() => loadExample('interactive')}>
                Interactive
              </Button>
            </div>

            <div className="flex items-center gap-2">
              <Button size="sm" variant="ghost" onClick={formatJson}>
                Format
              </Button>
              <Button size="sm" variant="ghost" onClick={clearEditor}>
                Clear
              </Button>
              <div className="border-l border-gray-300 dark:border-gray-600 h-6 mx-2" />
              <div className="flex gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
                <button
                  onClick={() => setLayout('split')}
                  className={`px-3 py-1 text-xs rounded ${
                    layout === 'split'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                      : 'text-gray-600 dark:text-gray-400'
                  }`}
                >
                  Split
                </button>
                <button
                  onClick={() => setLayout('editor')}
                  className={`px-3 py-1 text-xs rounded ${
                    layout === 'editor'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                      : 'text-gray-600 dark:text-gray-400'
                  }`}
                >
                  Editor
                </button>
                <button
                  onClick={() => setLayout('preview')}
                  className={`px-3 py-1 text-xs rounded ${
                    layout === 'preview'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm'
                      : 'text-gray-600 dark:text-gray-400'
                  }`}
                >
                  Preview
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* JSON Editor */}
          {(layout === 'split' || layout === 'editor') && (
            <div className={`${layout === 'split' ? 'w-1/2' : 'w-full'} flex flex-col border-r border-gray-200 dark:border-gray-700`}>
              <div className="bg-gray-100 dark:bg-gray-800 px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">JSON Schema Editor</h3>
              </div>
              <div className="flex-1 relative">
                <textarea
                  value={jsonInput}
                  onChange={(e) => handleJsonChange(e.target.value)}
                  className="absolute inset-0 w-full h-full p-4 font-mono text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border-0 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 resize-none"
                  spellCheck={false}
                  placeholder="Enter JSON schema here..."
                />
              </div>
              {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800 px-4 py-3">
                  <p className="text-sm text-red-800 dark:text-red-200 font-mono whitespace-pre-wrap">
                    {error}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Live Preview */}
          {(layout === 'split' || layout === 'preview') && (
            <div className={`${layout === 'split' ? 'w-1/2' : 'w-full'} flex flex-col bg-gray-50 dark:bg-gray-900`}>
              <div className="bg-gray-100 dark:bg-gray-800 px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Live Preview</h3>
              </div>
              <div className="flex-1 overflow-auto p-4">
                {schema ? (
                  <JSONUIRenderer schema={schema} debug={false} />
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <svg
                        className="mx-auto h-12 w-12 text-gray-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                      <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
                        {error ? 'Invalid JSON' : 'No Preview'}
                      </h3>
                      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        {error ? 'Fix the errors to see the preview' : 'Enter valid JSON to see the preview'}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Status Bar */}
        <div className="bg-gray-100 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-4 py-2">
          <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
            <div className="flex items-center gap-4">
              <span>Lines: {jsonInput.split('\n').length}</span>
              <span>Characters: {jsonInput.length}</span>
              <span className={`flex items-center gap-1 ${error ? 'text-red-600' : 'text-green-600'}`}>
                <span className={`w-2 h-2 rounded-full ${error ? 'bg-red-600' : 'bg-green-600'}`} />
                {error ? 'Invalid' : 'Valid'}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-500">
                Tip: Use Ctrl+Space for autocomplete • Ctrl+F to find
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
