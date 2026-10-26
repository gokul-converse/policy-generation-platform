/**
 * Policy domain types.
 */

export type DocumentElementType = 
  | 'title'
  | 'heading'
  | 'subheading'
  | 'paragraph'
  | 'clause'
  | 'subclause'
  | 'annexure';

export interface Paragraph {
  id: string;
  content: string;
  order: number;
  type?: DocumentElementType; // Optional for backward compatibility
  level?: number; // Heading level (1-6) or clause depth
}

export interface Policy {
  id: string;
  title?: string; // Policy title extracted from description
  description: string;
  paragraphs: Paragraph[];
  status: 'draft' | 'generated' | 'reviewed' | 'ui_generated';
  createdAt: Date;
  updatedAt: Date;
}

export interface GeneratePolicyRequest {
  description: string;
}

export interface GeneratePolicyResponse {
  policy: Policy;
}

export interface RegenerateParagraphRequest {
  paragraphId: string;
  instructions: string;
}

export interface RegenerateParagraphResponse {
  paragraph: Paragraph;
}

export interface GenerateUIRequest {
  policyId: string;
  instructions?: string;
}

export interface UIComponent {
  type: string;
  props: Record<string, any>;
  children?: UIComponent[];
}

export interface GeneratedUI {
  id: string;
  policyId: string;
  components: UIComponent[];
  json: string;
  createdAt: Date;
}

export interface GenerateUIResponse {
  ui: GeneratedUI;
}
