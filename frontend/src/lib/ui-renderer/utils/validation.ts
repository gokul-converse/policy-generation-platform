/**
 * JSON Schema Validation Utilities
 */

import { UISchema, UIComponentSchema, isUISchema, isUIComponentSchema } from '@/types/ui-schema';

export interface ValidationError {
  path: string;
  message: string;
  component?: UIComponentSchema;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

/**
 * Validate a UI schema
 */
export function validateUISchema(schema: unknown): ValidationResult {
  const errors: ValidationError[] = [];

  if (!schema || typeof schema !== 'object') {
    errors.push({
      path: 'root',
      message: 'Schema must be an object',
    });
    return { valid: false, errors };
  }

  // Check if it's a valid UISchema
  if (!isUISchema(schema) && !Array.isArray(schema)) {
    errors.push({
      path: 'root',
      message: 'Schema must have a version and components array, or be a components array',
    });
    return { valid: false, errors };
  }

  const components = isUISchema(schema) ? schema.components : schema;

  // Validate each component
  components.forEach((component, index) => {
    validateComponent(component, `components[${index}]`, errors);
  });

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Validate a single component
 */
function validateComponent(
  component: unknown,
  path: string,
  errors: ValidationError[]
): void {
  if (!isUIComponentSchema(component)) {
    errors.push({
      path,
      message: 'Component must have a type property',
      component: component as UIComponentSchema,
    });
    return;
  }

  // Validate required props for specific component types
  switch (component.type) {
    case 'button':
      if (!component.props?.label) {
        errors.push({
          path: `${path}.props.label`,
          message: 'Button requires a label',
          component,
        });
      }
      break;

    case 'input':
    case 'textarea':
    case 'select':
      if (!component.props?.name) {
        errors.push({
          path: `${path}.props.name`,
          message: `${component.type} requires a name`,
          component,
        });
      }
      break;

    case 'link':
      if (!component.props?.href) {
        errors.push({
          path: `${path}.props.href`,
          message: 'Link requires an href',
          component,
        });
      }
      if (!component.props?.content) {
        errors.push({
          path: `${path}.props.content`,
          message: 'Link requires content',
          component,
        });
      }
      break;

    case 'image':
      if (!component.props?.src) {
        errors.push({
          path: `${path}.props.src`,
          message: 'Image requires a src',
          component,
        });
      }
      if (!component.props?.alt) {
        errors.push({
          path: `${path}.props.alt`,
          message: 'Image requires alt text for accessibility',
          component,
        });
      }
      break;

    case 'table':
      if (!component.props?.columns || !Array.isArray(component.props.columns)) {
        errors.push({
          path: `${path}.props.columns`,
          message: 'Table requires columns array',
          component,
        });
      }
      if (!component.props?.data) {
        errors.push({
          path: `${path}.props.data`,
          message: 'Table requires data',
          component,
        });
      }
      break;

    case 'accordion':
      if (!component.props?.items || !Array.isArray(component.props.items)) {
        errors.push({
          path: `${path}.props.items`,
          message: 'Accordion requires items array',
          component,
        });
      }
      break;

    case 'tabs':
      if (!component.props?.items || !Array.isArray(component.props.items)) {
        errors.push({
          path: `${path}.props.items`,
          message: 'Tabs requires items array',
          component,
        });
      }
      break;
  }

  // Recursively validate children
  if (component.children && Array.isArray(component.children)) {
    component.children.forEach((child, index) => {
      validateComponent(child, `${path}.children[${index}]`, errors);
    });
  }
}

/**
 * Sanitize JSON to ensure safe rendering
 */
export function sanitizeUISchema(schema: any): UISchema | UIComponentSchema[] {
  if (isUISchema(schema)) {
    return {
      ...schema,
      components: schema.components.map(sanitizeComponent),
    };
  }

  if (Array.isArray(schema)) {
    return schema.map(sanitizeComponent);
  }

  return [];
}

/**
 * Sanitize a single component
 */
function sanitizeComponent(component: UIComponentSchema): UIComponentSchema {
  const sanitized: UIComponentSchema = {
    type: component.type,
    props: { ...component.props },
  };

  // Remove potentially dangerous props
  if (sanitized.props) {
    delete (sanitized.props as any).dangerouslySetInnerHTML;
    delete (sanitized.props as any).__html;
  }

  // Recursively sanitize children
  if (component.children && Array.isArray(component.children)) {
    sanitized.children = component.children.map(sanitizeComponent);
  }

  // Copy safe optional properties
  if (component.binding) sanitized.binding = component.binding;
  if (component?.condition) sanitized.condition = component.condition;

  return sanitized;
}

/**
 * Get a human-readable error summary
 */
export function getErrorSummary(result: ValidationResult): string {
  if (result.valid) {
    return 'Schema is valid';
  }

  const errorCount = result.errors.length;
  const summary = [`Found ${errorCount} validation error${errorCount !== 1 ? 's' : ''}:`];

  result.errors.slice(0, 5).forEach((error) => {
    summary.push(`  • ${error.path}: ${error.message}`);
  });

  if (errorCount > 5) {
    summary.push(`  ... and ${errorCount - 5} more`);
  }

  return summary.join('\n');
}
