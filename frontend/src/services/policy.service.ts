/**
 * Policy Service - API Integration Layer
 * 
 * This service provides the interface between the UI and backend.
 * Currently uses mock implementations, but structured for easy backend integration.
 * 
 * To integrate with backend:
 * 1. Update API_ENDPOINTS with actual backend URLs
 * 2. Replace mock service calls with apiClient calls
 * 3. Update error handling as needed
 */

import apiClient from './api-client';
import {
  Policy,
  Paragraph,
  GeneratePolicyRequest,
  GeneratePolicyResponse,
  RegenerateParagraphRequest,
  RegenerateParagraphResponse,
  GenerateUIRequest,
  GenerateUIResponse,
} from '@/types';

// Import mock services (remove when backend is ready)
import * as MockPolicyService from './mock-policy.service';

// API Endpoints - Update these when backend is ready
const API_ENDPOINTS = {
  generatePolicy: '/api/policy/generate',
  regenerateParagraph: '/api/policy/paragraph/regenerate',
  generateUI: '/api/policy/ui/generate',
} as const;

// Feature flag to toggle between mock and real API
const USE_MOCK_API = true; // Set to false when backend is ready

/**
 * Service: Generate Policy from Description
 * 
 * Backend endpoint: POST /api/policy/generate
 * Request body: { description: string }
 * Response: { policy: Policy }
 */
export const generatePolicy = async (
  description: string
): Promise<Policy> => {
  if (USE_MOCK_API) {
    const response = await MockPolicyService.generatePolicy({ description });
    return response.policy;
  }

  // Real API call (uncomment when backend is ready):
  // const response = await apiClient.post<GeneratePolicyResponse>(
  //   API_ENDPOINTS.generatePolicy,
  //   { description }
  // );
  // return response.data.policy;

  throw new Error('Real API not implemented yet');
};

/**
 * Service: Regenerate a Single Paragraph
 * 
 * Backend endpoint: POST /api/policy/paragraph/regenerate
 * Request body: { paragraphId: string, instructions: string }
 * Response: { paragraph: Paragraph }
 */
export const regenerateParagraph = async (
  paragraphId: string,
  instructions: string,
  currentParagraph: Paragraph
): Promise<Paragraph> => {
  if (USE_MOCK_API) {
    const response = await MockPolicyService.regenerateParagraph(
      { paragraphId, instructions },
      currentParagraph
    );
    return response.paragraph;
  }

  // Real API call (uncomment when backend is ready):
  // const response = await apiClient.post<RegenerateParagraphResponse>(
  //   API_ENDPOINTS.regenerateParagraph,
  //   { paragraphId, instructions }
  // );
  // return response.data.paragraph;

  throw new Error('Real API not implemented yet');
};

/**
 * Service: Generate UI from Policy
 * 
 * Backend endpoint: POST /api/policy/ui/generate
 * Request body: { policyId: string, instructions?: string }
 * Response: { ui: GeneratedUI }
 */
export const generateUI = async (
  policyId: string,
  policy: Policy,
  instructions?: string
): Promise<GenerateUIResponse['ui']> => {
  if (USE_MOCK_API) {
    const response = await MockPolicyService.generateUI(
      { policyId, instructions },
      policy
    );
    return response.ui;
  }

  // Real API call (uncomment when backend is ready):
  // const response = await apiClient.post<GenerateUIResponse>(
  //   API_ENDPOINTS.generateUI,
  //   { policyId, instructions }
  // );
  // return response.data.ui;

  throw new Error('Real API not implemented yet');
};
