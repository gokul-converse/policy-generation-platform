/**
 * UI Preview Component
 * Full-screen display of generated UI with minimal, distraction-free layout
 */

'use client';

import React, { useState } from 'react';
import { GeneratedUI } from '@/types';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { UIRenderer } from './ui-renderer';

interface UIPreviewProps {
  generatedUI: GeneratedUI;
  onRegenerateUI: (instructions: string) => void;
  isRegenerating: boolean;
  onBack?: () => void;
}

export const UIPreview: React.FC<UIPreviewProps> = ({
  generatedUI,
  onRegenerateUI,
  isRegenerating,
  onBack,
}) => {
  const [showJSON, setShowJSON] = useState(false);
  const [showRegenerateForm, setShowRegenerateForm] = useState(false);
  const [instructions, setInstructions] = useState('');

  const handleRegenerate = () => {
    if (instructions.trim()) {
      onRegenerateUI(instructions);
      setInstructions('');
      setShowRegenerateForm(false);
    }
  };

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      window.history.back();
    }
  };

  return (
    <div className="fixed inset-0 bg-white dark:bg-gray-900 z-50 overflow-hidden flex flex-col">
      {/* Minimal Header Bar */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              onClick={handleBack}
              variant="ghost"
              size="sm"
            >
              <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back
            </Button>
            <div className="w-px h-6 bg-gray-200 dark:bg-gray-700" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Generated UI Preview
            </h2>
          </div>
          
          <div className="flex items-center gap-2">
            {!showRegenerateForm && !showJSON && (
              <>
                <Button
                  onClick={() => setShowRegenerateForm(true)}
                  variant="outline"
                  size="sm"
                  disabled={isRegenerating}
                >
                  Regenerate UI
                </Button>
                <Button
                  onClick={() => setShowJSON(true)}
                  variant="outline"
                  size="sm"
                >
                  Show JSON
                </Button>
              </>
            )}
            
            {showJSON && (
              <Button
                onClick={() => setShowJSON(false)}
                variant="outline"
                size="sm"
              >
                Hide JSON
              </Button>
            )}
          </div>
        </div>

        {/* Regenerate Form - Inline */}
        {showRegenerateForm && (
          <div className="px-6 pb-4 border-t border-gray-100 dark:border-gray-800 pt-4">
            <div className="max-w-2xl">
              <Textarea
                label="How would you like to modify the UI?"
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                rows={2}
                placeholder="For example: 'Make the dashboard more compact' or 'Add more visual elements'"
              />
              <div className="flex gap-2 mt-3">
                <Button
                  onClick={handleRegenerate}
                  variant="primary"
                  size="sm"
                  disabled={!instructions.trim() || isRegenerating}
                  loading={isRegenerating}
                >
                  Regenerate
                </Button>
                <Button
                  onClick={() => {
                    setShowRegenerateForm(false);
                    setInstructions('');
                  }}
                  variant="outline"
                  size="sm"
                  disabled={isRegenerating}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* UI Preview Panel */}
        <div className={`${showJSON ? 'w-1/2' : 'w-full'} overflow-auto`}>
          <div className="p-8">
            <UIRenderer components={generatedUI.components} />
          </div>
        </div>

        {/* JSON Panel - Slide in from right */}
        {showJSON && (
          <div className="w-1/2 border-l border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 overflow-auto flex flex-col">
            <div className="flex-shrink-0 px-6 py-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                UI Component JSON
              </h3>
            </div>
            <div className="flex-1 overflow-auto">
              <pre className="p-6 text-xs text-gray-800 dark:text-gray-300 font-mono">
                {generatedUI.json}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
