/**
 * Mock Policy Service
 * 
 * Simulates backend responses with realistic delays and generated content.
 * Replace with real API calls when backend is ready.
 */

import {
  Policy,
  Paragraph,
  GeneratePolicyRequest,
  GeneratePolicyResponse,
  RegenerateParagraphRequest,
  RegenerateParagraphResponse,
  GenerateUIRequest,
  GenerateUIResponse,
  GeneratedUI,
  UIComponent,
} from '@/types';

// Simulated network delay
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Generate unique IDs
const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// Mock paragraph generation based on policy description
const generateMockParagraphs = (description: string): Paragraph[] => {
  const elements: Paragraph[] = [];
  let order = 0;

  // Title
  elements.push({
    id: generateId(),
    content: extractPolicyTitle(description),
    order: order++,
    type: 'title',
    level: 1,
  });

  // Introduction paragraph
  elements.push({
    id: generateId(),
    content: `This policy outlines the framework and guidelines for ${description.toLowerCase()}. It establishes clear expectations, responsibilities, and procedures to ensure consistent implementation across the organization.`,
    order: order++,
    type: 'paragraph',
  });

  // Section 1: Purpose and Scope
  elements.push({
    id: generateId(),
    content: '1. Purpose and Scope',
    order: order++,
    type: 'heading',
    level: 2,
  });

  elements.push({
    id: generateId(),
    content: `The purpose of this policy is to establish comprehensive guidelines and standards for ${description.toLowerCase()}. This policy applies to all employees, contractors, and third-party vendors who are engaged in activities related to this area of operation.`,
    order: order++,
    type: 'paragraph',
  });

  // Section 2: Definitions
  elements.push({
    id: generateId(),
    content: '2. Definitions',
    order: order++,
    type: 'heading',
    level: 2,
  });

  elements.push({
    id: generateId(),
    content: 'For the purposes of this policy, the following terms and definitions apply:',
    order: order++,
    type: 'paragraph',
  });

  elements.push({
    id: generateId(),
    content: '2.1. "Organization" refers to the entity implementing this policy and all its affiliated entities.',
    order: order++,
    type: 'clause',
    level: 1,
  });

  elements.push({
    id: generateId(),
    content: '2.2. "Personnel" includes all employees, contractors, consultants, and temporary workers.',
    order: order++,
    type: 'clause',
    level: 1,
  });

  // Section 3: Policy Statement
  elements.push({
    id: generateId(),
    content: '3. Policy Statement',
    order: order++,
    type: 'heading',
    level: 2,
  });

  elements.push({
    id: generateId(),
    content: `The organization is committed to maintaining the highest standards in ${description.toLowerCase()}. All personnel must adhere to the principles and guidelines outlined in this policy to ensure compliance, effectiveness, and continuous improvement.`,
    order: order++,
    type: 'paragraph',
  });

  // Section 4: Responsibilities
  elements.push({
    id: generateId(),
    content: '4. Responsibilities',
    order: order++,
    type: 'heading',
    level: 2,
  });

  elements.push({
    id: generateId(),
    content: '4.1. Executive Management',
    order: order++,
    type: 'subheading',
    level: 3,
  });

  elements.push({
    id: generateId(),
    content: 'Executive management is responsible for approving this policy, allocating necessary resources, and ensuring organizational compliance.',
    order: order++,
    type: 'paragraph',
  });

  elements.push({
    id: generateId(),
    content: '4.2. Department Heads',
    order: order++,
    type: 'subheading',
    level: 3,
  });

  elements.push({
    id: generateId(),
    content: 'Department heads must ensure that their teams understand and comply with this policy, and report any violations or concerns to appropriate authorities.',
    order: order++,
    type: 'paragraph',
  });

  // Section 5: Procedures
  elements.push({
    id: generateId(),
    content: '5. Implementation Procedures',
    order: order++,
    type: 'heading',
    level: 2,
  });

  elements.push({
    id: generateId(),
    content: 'The following procedures must be followed to ensure effective implementation:',
    order: order++,
    type: 'paragraph',
  });

  elements.push({
    id: generateId(),
    content: '5.1. All personnel must receive training on this policy within 30 days of its effective date or their hire date, whichever is later.',
    order: order++,
    type: 'clause',
    level: 1,
  });

  elements.push({
    id: generateId(),
    content: '5.2. Regular audits and assessments will be conducted to ensure ongoing compliance.',
    order: order++,
    type: 'clause',
    level: 1,
  });

  // Section 6: Compliance and Enforcement
  elements.push({
    id: generateId(),
    content: '6. Compliance and Enforcement',
    order: order++,
    type: 'heading',
    level: 2,
  });

  elements.push({
    id: generateId(),
    content: 'Non-compliance with this policy may result in disciplinary action, up to and including termination of employment or contract. All violations must be reported through the appropriate channels and will be investigated thoroughly.',
    order: order++,
    type: 'paragraph',
  });

  // Section 7: Review and Updates
  elements.push({
    id: generateId(),
    content: '7. Policy Review and Updates',
    order: order++,
    type: 'heading',
    level: 2,
  });

  elements.push({
    id: generateId(),
    content: 'This policy will be reviewed annually or as needed to ensure it remains current and effective. Updates will be communicated to all affected personnel in a timely manner.',
    order: order++,
    type: 'paragraph',
  });

  // Annexure
  elements.push({
    id: generateId(),
    content: 'Annexure I: Related Documents and References',
    order: order++,
    type: 'annexure',
    level: 1,
  });

  elements.push({
    id: generateId(),
    content: 'The following documents provide additional context and should be consulted in conjunction with this policy: organizational code of conduct, industry standards and regulations, relevant legal requirements, and internal operational procedures.',
    order: order++,
    type: 'paragraph',
  });

  return elements;
};

// Helper: Extract policy title from description
const extractPolicyTitle = (description: string): string => {
  // Simple title extraction - capitalize first letter of each word
  const words = description.trim().split(' ');
  const title = words
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
  
  // Add "Policy" if not already present
  if (!title.toLowerCase().includes('policy')) {
    return `${title} Policy`;
  }
  return title;
};

// Mock paragraph regeneration based on instructions
const regenerateMockParagraph = (paragraph: Paragraph, instructions: string): Paragraph => {
  return {
    ...paragraph,
    content: `**Regenerated based on instructions**: "${instructions}"\n\n${paragraph.content}\n\nThis paragraph has been updated to incorporate your feedback and align with the specified requirements. The content now reflects a more detailed approach while maintaining consistency with the overall policy framework.`,
  };
};

// Mock UI component generation
const generateMockUIComponents = (policy: Policy, instructions?: string): UIComponent[] => {
  const components: UIComponent[] = [
    {
      type: 'header',
      props: {
        title: 'Policy Dashboard',
        subtitle: `Generated from: ${policy.description}`,
        variant: 'primary',
      },
    },
    {
      type: 'section',
      props: {
        title: 'Policy Overview',
        layout: 'card',
      },
      children: [
        {
          type: 'text',
          props: {
            content: policy.description,
            weight: 'semibold',
            size: 'lg',
          },
        },
        {
          type: 'badge',
          props: {
            label: policy.status,
            color: 'green',
          },
        },
      ],
    },
    {
      type: 'grid',
      props: {
        columns: 2,
        gap: 4,
      },
      children: policy.paragraphs.slice(0, 4).map((para) => ({
        type: 'card',
        props: {
          title: para.content.split(':')[0].replace(/\*\*/g, ''),
          variant: 'bordered',
        },
        children: [
          {
            type: 'text',
            props: {
              content: para.content.substring(0, 150) + '...',
              size: 'sm',
            },
          },
        ],
      })),
    },
    {
      type: 'section',
      props: {
        title: 'Compliance Metrics',
        layout: 'full-width',
      },
      children: [
        {
          type: 'metrics',
          props: {
            items: [
              { label: 'Total Policies', value: '1', trend: 'up' },
              { label: 'Compliance Rate', value: '98%', trend: 'stable' },
              { label: 'Last Review', value: 'Today', trend: 'neutral' },
            ],
          },
        },
      ],
    },
  ];

  if (instructions) {
    components.push({
      type: 'alert',
      props: {
        message: `UI customized based on: "${instructions}"`,
        variant: 'info',
      },
    });
  }

  return components;
};

/**
 * Mock Service - Generate Policy
 */
export const generatePolicy = async (
  request: GeneratePolicyRequest
): Promise<GeneratePolicyResponse> => {
  await delay(2000); // Simulate API delay

  const policyId = generateId();
  const paragraphs = generateMockParagraphs(request.description);
  
  // Extract title from first element if it's a title type
  const titleElement = paragraphs.find(p => p.type === 'title');
  const title = titleElement ? titleElement.content : extractPolicyTitle(request.description);

  const policy: Policy = {
    id: policyId,
    title,
    description: request.description,
    paragraphs,
    status: 'generated',
    createdAt: new Date(),
    updatedAt: new Date(),
  };

  return { policy };
};

/**
 * Mock Service - Regenerate Paragraph
 */
export const regenerateParagraph = async (
  request: RegenerateParagraphRequest,
  currentParagraph: Paragraph
): Promise<RegenerateParagraphResponse> => {
  await delay(1500); // Simulate API delay

  const updatedParagraph = regenerateMockParagraph(currentParagraph, request.instructions);

  return { paragraph: updatedParagraph };
};

/**
 * Mock Service - Generate UI
 */
export const generateUI = async (
  request: GenerateUIRequest,
  policy: Policy
): Promise<GenerateUIResponse> => {
  await delay(3000); // Simulate cloud model processing delay

  const components = generateMockUIComponents(policy, request.instructions);

  const ui: GeneratedUI = {
    id: generateId(),
    policyId: request.policyId,
    components,
    json: JSON.stringify(components, null, 2),
    createdAt: new Date(),
  };

  return { ui };
};
