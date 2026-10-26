/**
 * Policy Paragraph Component
 * Displays a single paragraph with inline editing capability
 */

'use client';

import React, { useState } from 'react';
import { Paragraph } from '@/types';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface PolicyParagraphProps {
  paragraph: Paragraph;
  onRegenerate: (paragraphId: string, instructions: string) => void;
  isRegenerating: boolean;
}

export const PolicyParagraph: React.FC<PolicyParagraphProps> = ({
  paragraph,
  onRegenerate,
  isRegenerating,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [instructions, setInstructions] = useState('');
  const [isHovered, setIsHovered] = useState(false);

  const handleRegenerate = () => {
    if (instructions.trim()) {
      onRegenerate(paragraph.id, instructions);
      setInstructions('');
      setIsEditing(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setInstructions('');
  };

  return (
    <div
      className="relative group mb-4 p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Edit Button - Shows on hover */}
      {!isEditing && isHovered && !isRegenerating && (
        <button
          onClick={() => setIsEditing(true)}
          className="absolute top-2 right-2 p-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors shadow-sm"
          title="Edit this paragraph"
        >
          <svg
            className="w-4 h-4 text-gray-600 dark:text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
            />
          </svg>
        </button>
      )}

      {/* Paragraph Content */}
      <div className="prose dark:prose-invert max-w-none">
        <p className="text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">
          {paragraph.content}
        </p>
      </div>

      {/* Inline Edit Form */}
      {isEditing && (
        <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <Textarea
            label="Regeneration Instructions"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            rows={3}
            placeholder="Provide specific instructions for regenerating this paragraph. For example: 'Make this more concise' or 'Add more technical details about security protocols'"
            helperText="Describe how you want this paragraph to be improved"
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
              onClick={handleCancel}
              variant="outline"
              size="sm"
              disabled={isRegenerating}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Regenerating Indicator */}
      {isRegenerating && (
        <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
          <p className="text-sm text-yellow-800 dark:text-yellow-200 flex items-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Regenerating paragraph...
          </p>
        </div>
      )}
    </div>
  );
};
