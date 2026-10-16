/**
 * Policy Description Form Component
 * Step 1: Initial screen for policy description input
 */

'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardBody, CardFooter } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';

interface PolicyDescriptionFormProps {
  onGenerate: (description: string) => void;
  loading?: boolean;
}

export const PolicyDescriptionForm: React.FC<PolicyDescriptionFormProps> = ({
  onGenerate,
  loading = false,
}) => {
  const [description, setDescription] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (description.trim()) {
      onGenerate(description);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <Card>
        <CardHeader
          title="Generate Policy"
          subtitle="Describe the policy you want to create. The more detail you provide, the better the generated policy will be."
        />
        <form onSubmit={handleSubmit}>
          <CardBody>
            <Textarea
              label="Policy Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={8}
              placeholder="Describe your policy here. For example: 'Create a comprehensive remote work policy that covers work hours, communication expectations, equipment provisions, and security requirements for employees working from home.'"
              required
              helperText={`${description.length} characters`}
            />
          </CardBody>
          <CardFooter className="flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              disabled={!description.trim() || loading}
            >
              Generate Policy
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
};
