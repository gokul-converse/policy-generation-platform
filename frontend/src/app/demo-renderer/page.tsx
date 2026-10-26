/**
 * JSON UI Renderer Demo Page
 * Demonstrates the renderer with interactive examples
 */

'use client';

import React from 'react';
import { JSONUIRenderer } from '@/lib/ui-renderer';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { UISchema } from '@/types/ui-schema';
import { Navbar } from '@/components/layout/navbar';

// Import example JSONs
import fullAppExampleJson from '@/lib/ui-renderer/examples/full-app-example.json';
import dashboardExampleJson from '@/lib/ui-renderer/examples/dashboard-example.json';
import formExampleJson from '@/lib/ui-renderer/examples/form-example.json';
import interactiveExampleJson from '@/lib/ui-renderer/examples/interactive-example.json';

const fullAppExample = fullAppExampleJson as UISchema;
const dashboardExample = dashboardExampleJson as UISchema;
const formExample = formExampleJson as UISchema;
const interactiveExample = interactiveExampleJson as UISchema;

type ExampleKey = 'fullApp' | 'dashboard' | 'form' | 'interactive';

const examples: Record<ExampleKey, { title: string; description: string; schema: any }> = {
  fullApp: {
    title: 'Full Application',
    description: 'Complete policy generation platform with workflow, stats, and table',
    schema: fullAppExample,
  },
  dashboard: {
    title: 'Dashboard',
    description: 'Analytics dashboard with metrics, charts, and data tables',
    schema: dashboardExample,
  },
  form: {
    title: 'Form',
    description: 'Registration form with validation and various input types',
    schema: formExample,
  },
  interactive: {
    title: 'Interactive',
    description: 'Accordions, tabs, progress bars, and more',
    schema: interactiveExample,
  },
};

export default function RendererDemoPage() {
  const [activeExample, setActiveExample] = React.useState<ExampleKey>('fullApp');
  const [showJson, setShowJson] = React.useState(false);

  const currentExample = examples[activeExample];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navbar title="Examples Demo" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            JSON UI Renderer Examples
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Interactive examples of the JSON-driven UI system
          </p>
        </div>

        {/* Show JSON Toggle */}
        <div className="mb-6 flex justify-end">
          <Button
            variant={showJson ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setShowJson(!showJson)}
          >
            {showJson ? 'Hide' : 'Show'} JSON
          </Button>
        </div>
        {/* Example Selector */}
        <div className="mb-6">
          <div className="flex gap-3">
            {(Object.keys(examples) as ExampleKey[]).map((key) => (
              <button
                key={key}
                onClick={() => setActiveExample(key)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeExample === key
                    ? 'bg-blue-600 text-white'
                    : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
              >
                {examples[key].title}
              </button>
            ))}
          </div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            {currentExample.description}
          </p>
        </div>

        {/* Two Column Layout: Rendered UI and JSON */}
        <div className={`grid ${showJson ? 'grid-cols-2' : 'grid-cols-1'} gap-6`}>
          {/* Rendered UI */}
          <div>
            <Card>
              <CardHeader title="Rendered Output" />
              <CardBody>
                <JSONUIRenderer schema={currentExample.schema} debug={false} />
              </CardBody>
            </Card>
          </div>

          {/* JSON Source */}
          {showJson && (
            <div>
              <Card>
                <CardHeader
                  title="JSON Schema"
                  action={
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        navigator.clipboard.writeText(
                          JSON.stringify(currentExample.schema, null, 2)
                        );
                      }}
                    >
                      Copy
                    </Button>
                  }
                />
                <CardBody>
                  <pre className="text-xs overflow-auto max-h-[600px] bg-gray-900 dark:bg-gray-950 text-gray-100 p-4 rounded-lg">
                    {JSON.stringify(currentExample.schema, null, 2)}
                  </pre>
                </CardBody>
              </Card>
            </div>
          )}
        </div>

        {/* Documentation Link */}
        <div className="mt-8 p-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">
            📚 Documentation
          </h3>
          <p className="text-blue-800 dark:text-blue-200 mb-4">
            Learn how to use the JSON UI Renderer and add custom components.
          </p>
          <div className="flex gap-3">
            <Button
              variant="primary"
              size="sm"
              onClick={() => window.open('/JSON-UI-RENDERER.md', '_blank')}
            >
              View Documentation
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.href = '/'}
            >
              Back to Home
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
