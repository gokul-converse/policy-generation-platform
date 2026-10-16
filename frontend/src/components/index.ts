/**
 * Reusable UI components.
 *
 * Organise components into sub-directories by category:
 *   components/ui/        – primitive building blocks (Button, Input, Modal…)
 *   components/layout/   – page-level structural components (Header, Sidebar…)
 *   components/features/ – feature-specific composite components
 *
 * This barrel export re-exports components for convenient importing.
 *
 * Example:
 *   export { Button } from './ui/button';
 */

// UI Components
export { Button } from './ui/button';
export { Card, CardHeader, CardBody, CardFooter } from './ui/card';
export { Textarea } from './ui/textarea';
export { Spinner, LoadingOverlay } from './ui/spinner';

// Feature Components
export { PolicyDescriptionForm } from './features/policy-description-form';
export { PolicyDocument } from './features/policy-document';
export { PolicyDocumentElement } from './features/policy-document-element';
export { UIPreview } from './features/ui-preview';
export { UIRenderer } from './features/ui-renderer';
