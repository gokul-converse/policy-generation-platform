/**
 * Policy Document Component
 * Displays the complete policy in a PDF-like document format
 */

'use client';

import React from 'react';
import { Policy } from '@/types';
import { Button } from '@/components/ui/button';
import { PolicyDocumentElement } from './policy-document-element';

interface PolicyDocumentProps {
  policy: Policy;
  onRegenerateParagraph: (elementId: string, instructions: string) => void;
  onGenerateUI: () => void;
  isRegenerating: boolean;
  regeneratingParagraphId: string | null;
}

export const PolicyDocument: React.FC<PolicyDocumentProps> = ({
  policy,
  onRegenerateParagraph,
  onGenerateUI,
  isRegenerating,
  regeneratingParagraphId,
}) => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Document Container - PDF-like */}
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Document Paper */}
        <div className="bg-white dark:bg-gray-800 shadow-lg rounded-sm min-h-[800px]">
          {/* Document Content with proper padding like a real document */}
          <div className="policy-document px-12 py-16 md:px-16 md:py-20">
            {/* Document Elements */}
            <div className="space-y-0">
              {policy.paragraphs.map((element) => (
                <PolicyDocumentElement
                  key={element.id}
                  element={element}
                  onRegenerate={onRegenerateParagraph}
                  isRegenerating={isRegenerating && regeneratingParagraphId === element.id}
                />
              ))}
            </div>

            {/* Document Footer Spacing */}
            <div className="mt-16 pt-8 border-t border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-500 dark:text-gray-500 text-center">
                Policy generated on {new Date(policy.createdAt).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>

        {/* Action Bar - Fixed at bottom */}
        <div className="sticky bottom-6 mt-8 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl p-4 no-print">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              <p className="font-medium">{policy.title || 'Policy Document'}</p>
              <p className="text-xs mt-0.5">
                {policy.paragraphs.length} elements • Hover to edit any section
              </p>
            </div>
            <Button
              onClick={onGenerateUI}
              variant="primary"
              size="lg"
            >
              Generate UI
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
