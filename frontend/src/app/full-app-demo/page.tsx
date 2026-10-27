/**
 * Full Application Demo Page
 * Complete policy generation platform rendered from JSON
 */

'use client';

import React from 'react';
import { JSONUIRenderer } from '@/lib/ui-renderer';
import { UISchema } from '@/types/ui-schema';
import { Navbar } from '@/components/layout/navbar';
import fullAppSchemaJson from '@/lib/ui-renderer/examples/full-app-example.json';

const fullAppSchema = fullAppSchemaJson as UISchema;

export default function FullAppDemoPage() {
  const [showSource, setShowSource] = React.useState(false);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navbar title="Full App Demo" />
      {/* Toggle Button - Fixed Position */}
      <button
        onClick={() => setShowSource(!showSource)}
        className="fixed bottom-6 right-6 z-50 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-lg transition-colors flex items-center gap-2"
      >
        <span>{showSource ? '👁️ Hide' : '📝 Show'} JSON Source</span>
      </button>

      {/* JSON Source Modal */}
      {showSource && (
        <div className="fixed inset-0 z-40 bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                JSON Schema Source
              </h2>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(fullAppSchema, null, 2));
                    alert('JSON copied to clipboard!');
                  }}
                  className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded transition-colors"
                >
                  📋 Copy
                </button>
                <button
                  onClick={() => setShowSource(false)}
                  className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded transition-colors"
                >
                  ✕ Close
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-auto p-4">
              <pre className="text-xs bg-gray-900 dark:bg-gray-950 text-gray-100 p-4 rounded-lg overflow-auto">
                {JSON.stringify(fullAppSchema, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Rendered Application */}
      <JSONUIRenderer schema={fullAppSchema} />
    </div>
  );
}
