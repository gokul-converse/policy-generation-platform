/**
 * Policy Document Element Component
 * Displays a single document element (title, heading, paragraph, clause, annexure) with inline editing
 */

'use client';

import React, { useState } from 'react';
import { Paragraph } from '@/types';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface PolicyDocumentElementProps {
  element: Paragraph;
  onRegenerate: (elementId: string, instructions: string) => void;
  isRegenerating: boolean;
}

export const PolicyDocumentElement: React.FC<PolicyDocumentElementProps> = ({
  element,
  onRegenerate,
  isRegenerating,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [instructions, setInstructions] = useState('');
  const [isHovered, setIsHovered] = useState(false);
  const [isIconHovered, setIsIconHovered] = useState(false);

  const handleRegenerate = () => {
    if (instructions.trim()) {
      onRegenerate(element.id, instructions);
      setInstructions('');
      setIsEditing(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setInstructions('');
  };

  const handleMouseEnterElement = () => {
    setIsHovered(true);
  };

  const handleMouseLeaveElement = () => {
    setIsHovered(false);
  };

  const handleMouseEnterIcon = () => {
    setIsIconHovered(true);
    setIsHovered(true); // Keep element highlighted when hovering icon
  };

  const handleMouseLeaveIcon = () => {
    setIsIconHovered(false);
  };

  // Show icon if either element or icon is hovered
  const showEditIcon = !isEditing && (isHovered || isIconHovered) && !isRegenerating;

  // Determine styling based on element type
  const getElementStyles = () => {
    const type = element.type || 'paragraph';
    
    switch (type) {
      case 'title':
        return 'text-3xl md:text-4xl font-bold text-gray-900 dark:text-gray-50 mb-6 leading-tight';
      case 'heading':
        return 'text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-50 mt-8 mb-4 leading-tight';
      case 'subheading':
        return 'text-lg md:text-xl font-semibold text-gray-800 dark:text-gray-100 mt-6 mb-3 leading-snug';
      case 'clause':
        return 'text-base text-gray-700 dark:text-gray-300 my-2 leading-relaxed pl-4';
      case 'subclause':
        return 'text-base text-gray-700 dark:text-gray-300 my-2 leading-relaxed pl-8';
      case 'annexure':
        return 'text-lg font-semibold text-gray-800 dark:text-gray-100 mt-10 mb-4 leading-snug';
      case 'paragraph':
      default:
        return 'text-base text-gray-700 dark:text-gray-300 my-4 leading-relaxed';
    }
  };

  // Determine if element should have top margin
  const getMarginTop = () => {
    const type = element.type || 'paragraph';
    return ['title', 'heading', 'subheading', 'annexure'].includes(type);
  };

  return (
    <div
      className={`relative group ${getMarginTop() ? 'mt-2' : ''}`}
      onMouseEnter={handleMouseEnterElement}
      onMouseLeave={handleMouseLeaveElement}
    >
      {/* Edit Button - Top Right Corner */}
      {showEditIcon && (
        <button
          onClick={() => setIsEditing(true)}
          onMouseEnter={handleMouseEnterIcon}
          onMouseLeave={handleMouseLeaveIcon}
          className="absolute -top-1 -right-1 p-1.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-blue-50 dark:hover:bg-gray-700 hover:border-blue-400 dark:hover:border-blue-600 transition-all shadow-sm z-10"
          title="Edit this element"
        >
          <svg
            className="w-3.5 h-3.5 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
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

      {/* Element Content */}
      <div className={getElementStyles()}>
        {element.content}
      </div>

      {/* Inline Edit Form */}
      {isEditing && (
        <div className="my-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <Textarea
            label="Regeneration Instructions"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            rows={2}
            placeholder="Provide specific instructions for regenerating this element. For example: 'Make this more concise' or 'Add more detail'"
            helperText="Describe how you want this element to be improved"
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
        <div className="my-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
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
            Regenerating...
          </p>
        </div>
      )}
    </div>
  );
};
