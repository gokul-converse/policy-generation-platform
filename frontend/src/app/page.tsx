/**
 * Policy Generator - Main Application Page
 * 
 * This page orchestrates the entire policy generation workflow:
 * 1. Policy Description Input
 * 2. Policy Document Review & Editing
 * 3. UI Generation & Preview
 */

'use client';

import React, { useState } from 'react';
import { Policy, GeneratedUI } from '@/types';
import {
  PolicyDescriptionForm,
  PolicyDocument,
  UIPreview,
  LoadingOverlay,
} from '@/components';
import { Navbar } from '@/components/layout/navbar';
import * as PolicyService from '@/services/policy.service';

type AppStep = 'description' | 'document' | 'ui-preview';

export default function HomePage() {
  // Application state
  const [step, setStep] = useState<AppStep>('description');
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [generatedUI, setGeneratedUI] = useState<GeneratedUI | null>(null);

  // Loading states
  const [isGeneratingPolicy, setIsGeneratingPolicy] = useState(false);
  const [isRegeneratingParagraph, setIsRegeneratingParagraph] = useState(false);
  const [regeneratingParagraphId, setRegeneratingParagraphId] = useState<string | null>(null);
  const [isGeneratingUI, setIsGeneratingUI] = useState(false);

  // Error state
  const [error, setError] = useState<string | null>(null);

  /**
   * Handler:   from Description
   */
  const handleGeneratePolicy = async (description: string) => {
    setIsGeneratingPolicy(true);
    setError(null);

    try {
      const generatedPolicy = await PolicyService.generatePolicy(description);
      setPolicy(generatedPolicy);
      setStep('document');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate policy');
      console.error('Policy generation error:', err);
    } finally {
      setIsGeneratingPolicy(false);
    }
  };

  /**
   * Handler: Regenerate a Single Element
   */
  const handleRegenerateElement = async (elementId: string, instructions: string) => {
    if (!policy) return;

    setIsRegeneratingParagraph(true);
    setRegeneratingParagraphId(elementId);
    setError(null);

    try {
      const currentElement = policy.paragraphs.find(p => p.id === elementId);
      if (!currentElement) throw new Error('Element not found');

      const updatedElement = await PolicyService.regenerateParagraph(
        elementId,
        instructions,
        currentElement
      );

      // Update policy with regenerated element
      setPolicy({
        ...policy,
        paragraphs: policy.paragraphs.map(p =>
          p.id === elementId ? updatedElement : p
        ),
        updatedAt: new Date(),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate element');
      console.error('Element regeneration error:', err);
    } finally {
      setIsRegeneratingParagraph(false);
      setRegeneratingParagraphId(null);
    }
  };

  /**
   * Handler: Generate UI from Policy
   */
  const handleGenerateUI = async () => {
    if (!policy) return;

    setIsGeneratingUI(true);
    setError(null);

    try {
      const ui = await PolicyService.generateUI(policy.id, policy);
      setGeneratedUI(ui);
      setPolicy({ ...policy, status: 'ui_generated' });
      setStep('ui-preview');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate UI');
      console.error('UI generation error:', err);
    } finally {
      setIsGeneratingUI(false);
    }
  };

  /**
   * Handler: Regenerate UI with Instructions
   */
  const handleRegenerateUI = async (instructions: string) => {
    if (!policy) return;

    setIsGeneratingUI(true);
    setError(null);

    try {
      const ui = await PolicyService.generateUI(policy.id, policy, instructions);
      setGeneratedUI(ui);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate UI');
      console.error('UI regeneration error:', err);
    } finally {
      setIsGeneratingUI(false);
    }
  };

  return (
    <>
      {/* Navigation Bar */}
      <Navbar />
      
      {/* Main Content */}
      <main className="min-h-screen bg-white dark:bg-gray-800">
        {/* Breadcrumb Navigation */}
        {step !== 'description' && (
          <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
              <nav className="flex items-center space-x-2 text-sm">
                <button
                  onClick={() => setStep('description')}
                  className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium transition-colors"
                >
                  Policy Generator
                </button>
                
                {step === 'document' && (
                  <>
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    <span className="text-gray-900 dark:text-gray-100 font-medium">
                      {policy?.title || 'Policy Document'}
                    </span>
                  </>
                )}
                
                {step === 'ui-preview' && (
                  <>
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    <button
                      onClick={() => setStep('document')}
                      className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium transition-colors"
                    >
                      {policy?.title || 'Policy Document'}
                    </button>
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    <span className="text-gray-900 dark:text-gray-100 font-medium">
                      Generated UI
                    </span>
                  </>
                )}
              </nav>
            </div>
          </div>
        )}

        {/* Header - Only show on description step */}
        {/* {step === 'description' && (
          <div className="bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto text-center">
              <h1 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-gray-100 tracking-tight">
                Policy Generator
              </h1>
              <p className="mt-4 text-lg text-gray-600 dark:text-gray-400">
                Create comprehensive, professional policy documents with AI assistance
              </p>
            </div>
          </div>
        )} */}

        {/* Error Display */}
        {error && step === 'description' && (
          <div className="max-w-4xl mx-auto px-4 mb-6">
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <p className="text-red-800 dark:text-red-200">{error}</p>
            </div>
          </div>
        )}

        {/* Step Content */}
        {step === 'description' && (
          <div className="bg-gray-50 dark:bg-gray-900 py-8 px-4 sm:px-6 lg:px-8">
            <PolicyDescriptionForm
              onGenerate={handleGeneratePolicy}
              loading={isGeneratingPolicy}
            />
          </div>
        )}

        {step === 'document' && policy && (
          <PolicyDocument
            policy={policy}
            onRegenerateParagraph={handleRegenerateElement}
            onGenerateUI={handleGenerateUI}
            isRegenerating={isRegeneratingParagraph}
            regeneratingParagraphId={regeneratingParagraphId}
          />
        )}

        {step === 'ui-preview' && generatedUI && (
          <UIPreview
            generatedUI={generatedUI}
            onRegenerateUI={handleRegenerateUI}
            isRegenerating={isGeneratingUI}
            onBack={() => setStep('document')}
          />
        )}
      </main>

      {/* Loading Overlays */}
      {isGeneratingPolicy && <LoadingOverlay message="Generating policy..." />}
      {isGeneratingUI && <LoadingOverlay message="Generating UI..." />}
    </>
  );
}
