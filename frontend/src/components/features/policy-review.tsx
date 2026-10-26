/**
 * Policy Review Component
 * Step 2 & 3: Display generated policy with paragraph editing
 */

'use client';

import React, { useState } from 'react';
import { Policy } from '@/types';
import { Card, CardHeader, CardBody, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PolicyParagraph } from './policy-paragraph';

interface PolicyReviewProps {
  policy: Policy;
  onRegenerateParagraph: (paragraphId: string, instructions: string) => void;
  onGenerateUI: () => void;
  isRegenerating: boolean;
  regeneratingParagraphId: string | null;
}

export const PolicyReview: React.FC<PolicyReviewProps> = ({
  policy,
  onRegenerateParagraph,
  onGenerateUI,
  isRegenerating,
  regeneratingParagraphId,
}) => {
  return (
    <div className="max-w-5xl mx-auto">
      <Card>
        <CardHeader
          title="Review Generated Policy"
          subtitle={policy.description}
          action={
            <span className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 text-xs font-semibold rounded-full">
              {policy.status.toUpperCase().replace('_', ' ')}
            </span>
          }
        />
        <CardBody>
          <div className="space-y-2">
            {policy.paragraphs.map((paragraph) => (
              <PolicyParagraph
                key={paragraph.id}
                paragraph={paragraph}
                onRegenerate={onRegenerateParagraph}
                isRegenerating={isRegenerating && regeneratingParagraphId === paragraph.id}
              />
            ))}
          </div>
        </CardBody>
        <CardFooter className="flex justify-between items-center">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {policy.paragraphs.length} paragraph(s) • Hover over any paragraph to edit
          </p>
          <Button
            onClick={onGenerateUI}
            variant="primary"
            size="lg"
          >
            Generate UI
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};
