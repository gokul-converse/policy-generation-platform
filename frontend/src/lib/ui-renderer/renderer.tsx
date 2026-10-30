/**
 * JSON UI Renderer
 * Main renderer component that converts JSON schemas to React components
 */

'use client';

import React from 'react';
import { UIComponentSchema, UISchema, isUISchema } from '@/types/ui-schema';
import { componentRegistry } from './registry';
import { executeAction, actionRegistry } from './actions/action-handler';
import { mergeStyles } from './utils/css-converter';
import { ThemeProvider } from './theme-provider';

// Import all component implementations
import * as LayoutComponents from './components/layout';
import * as TypographyComponents from './components/typography';
import * as UIElements from './components/ui-elements';
import * as FormComponents from './components/forms';
import * as InteractiveComponents from './components/interactive';
import * as AdvancedInteractiveComponents from './components/advanced-interactive';
import * as DataDisplayComponents from './components/data-display';
import * as NavigationComponents from './components/navigation';
import * as IconComponents from './components/icons';

// Register all components
componentRegistry.registerMany({
  // Layout
  container: LayoutComponents.Container,
  grid: LayoutComponents.Grid,
  row: LayoutComponents.Row,
  column: LayoutComponents.Column,
  stack: LayoutComponents.Stack,
  spacer: LayoutComponents.Spacer,
  
  // Typography
  text: TypographyComponents.Text,
  heading: TypographyComponents.Heading,
  paragraph: TypographyComponents.Paragraph,
  link: TypographyComponents.Link,
  
  // UI Elements
  button: UIElements.Button,
  badge: UIElements.Badge,
  alert: UIElements.Alert,
  card: UIElements.Card,
  divider: UIElements.Divider,
  image: UIElements.Image,
  
  // Forms
  form: FormComponents.Form,
  input: FormComponents.Input,
  textarea: FormComponents.Textarea,
  select: FormComponents.Select,
  checkbox: FormComponents.Checkbox,
  radio: FormComponents.Radio,
  switch: FormComponents.Switch,
  
  // Interactive
  accordion: InteractiveComponents.Accordion,
  tabs: InteractiveComponents.Tabs,
  modal: AdvancedInteractiveComponents.Modal,
  dropdown: AdvancedInteractiveComponents.Dropdown,
  tooltip: AdvancedInteractiveComponents.Tooltip,
  stepper: AdvancedInteractiveComponents.Stepper,
  timeline: AdvancedInteractiveComponents.Timeline,
  statCard: AdvancedInteractiveComponents.StatCard,
  infoCard: AdvancedInteractiveComponents.InfoCard,
  
  // Icons
  icon: IconComponents.Icon,
  
  // Data Display
  table: DataDisplayComponents.Table,
  list: DataDisplayComponents.List,
  metrics: DataDisplayComponents.Metrics,
  progress: DataDisplayComponents.Progress,
  chart: DataDisplayComponents.Chart,
  
  // Navigation
  nav: NavigationComponents.Nav,
  breadcrumb: NavigationComponents.Breadcrumb,
  pagination: NavigationComponents.Pagination,
});

// ============================================================================
// Renderer Props
// ============================================================================

export interface JSONUIRendererProps {
  /** JSON schema or component array */
  schema: UISchema | UIComponentSchema[];
  /** Custom data context for bindings */
  dataContext?: Record<string, any>;
  /** Error fallback component */
  errorFallback?: React.ComponentType<{ error: Error }>;
  /** Show debug info */
  debug?: boolean;
  /** Action callback for handling button clicks, form submissions */
  onAction?: (actionId: string, context: any) => Promise<void>;
}

// ============================================================================
// Component Renderer
// ============================================================================

const ComponentRenderer: React.FC<{
  component: UIComponentSchema;
  dataContext?: Record<string, any>;
  debug?: boolean;
  onAction?: (actionId: string, context: any) => Promise<void>;
}> = ({ component, dataContext, debug, onAction }) => {
  // Handle conditional rendering
  if (component?.condition) {
    try {
      // In a real implementation, evaluate condition expression
      // For now, we'll just check if it's truthy
      const shouldRender = evaluateCondition(component.condition, dataContext);
      if (!shouldRender) return null;
    } catch (error) {
      console.error('Condition evaluation error:', error);
      return null;
    }
  }

  // Get component from registry
  const Component = componentRegistry.get(component?.type);

  if (!Component) {
    if (debug) {
      return (
        <div className="p-4 border-2 border-red-500 bg-red-50 dark:bg-red-900/20 rounded">
          <p className="text-red-800 dark:text-red-200 font-semibold">
            Unknown component type: {component.type}
          </p>
        </div>
      );
    }
    console.warn(`Unknown component type: ${component.type}`);
    return null;
  }

  // Resolve data binding
  const props = { ...component.props };
  if (component.binding && dataContext) {
    const boundData = resolvePath(dataContext, component.binding);
    Object.assign(props, boundData);
  }

  // Merge CSS styles
  const { className, style } = mergeStyles(
    props.className || '',
    props.style || {},
    props.css || component.props?.style
  );
  props.className = className;
  props.style = style;

  // Add action handlers
  if (props.onClick && onAction) {
    props.onClick = () => handleAction(props.onClick, {}, onAction);
  }
  if (props.onSubmit && onAction) {
    const originalOnSubmit = props.onSubmit;
    props.onSubmit = (e: React.FormEvent) => {
      e?.preventDefault();
      const formData = extractFormData(e);
      handleAction(originalOnSubmit, { formData }, onAction);
    };
  }

  // Render children recursively
  const renderChildren = () => {
    if (!component.children || component.children.length === 0) {
      return undefined;
    }

    return component.children.map((child, index) => (
      <ComponentRenderer
        key={child.props?.id || index}
        component={child}
        dataContext={dataContext}
        debug={debug}
        onAction={onAction}
      />
    ));
  };

  // Special handling for components that need custom child rendering
  if (component.type === 'accordion' || component.type === 'tabs' || component.type === 'list') {
    return (
      <Component
        {...props}
        renderChild={(child: UIComponentSchema) => (
          <ComponentRenderer component={child} dataContext={dataContext} debug={debug} onAction={onAction} />
        )}
      />
    );
  }

  return <Component {...props}>{renderChildren()}</Component>;
};

// ============================================================================
// Main Renderer Component
// ============================================================================

export const JSONUIRenderer: React.FC<JSONUIRendererProps> = ({
  schema,
  dataContext = {},
  errorFallback: ErrorFallback,
  debug = false,
  onAction,
}) => {
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    setError(null);
    
    // Register actions from schema
    if (isUISchema(schema) && schema.actions) {
      schema.actions.forEach((action) => {
        actionRegistry.register(action);
      });
    }
  }, [schema]);

  if (error) {
    if (ErrorFallback) {
      return <ErrorFallback error={error} />;
    }
    return (
      <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <h3 className="text-red-800 dark:text-red-200 font-semibold mb-2">Rendering Error</h3>
        <p className="text-red-700 dark:text-red-300 text-sm">{error.message}</p>
      </div>
    );
  }

  try {
    // Normalize input to component array
    const components: UIComponentSchema[] = isUISchema(schema)
      ? schema.components
      : Array.isArray(schema)
      ? schema
      : [];

    if (components.length === 0) {
      return debug ? (
        <div className="p-4 border border-gray-300 dark:border-gray-600 rounded bg-gray-50 dark:bg-gray-800">
          <p className="text-gray-600 dark:text-gray-400">No components to render</p>
        </div>
      ) : null;
    }

    // Extract theme if available
    const theme = isUISchema(schema) ? schema.theme : undefined;

    return (
      <ThemeProvider theme={theme}>
        <div className="ui-renderer">
          {components.map((component, index) => (
            <ComponentRenderer
              key={component.props?.id || index}
              component={component}
              dataContext={dataContext}
              debug={debug}
              onAction={onAction}
            />
          ))}
        </div>
      </ThemeProvider>
    );
  } catch (err) {
    const error = err instanceof Error ? err : new Error('Unknown rendering error');
    setError(error);
    return null;
  }
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Evaluate a condition expression
 * In a real implementation, this would use a safe expression evaluator
 */
function evaluateCondition(condition: string, context?: Record<string, any>): boolean {
  // Placeholder implementation
  // In production, use a safe expression evaluator like jsonata or jexl
  return true;
}

/**
 * Resolve a path in an object (e.g., "user.name" -> context.user.name)
 */
function resolvePath(obj: any, path: string): any {
  return path.split('.').reduce((current, key) => current?.[key], obj);
}

/**
 * Handle action execution
 */
async function handleAction(
  actionId: string,
  context: any,
  onAction?: (actionId: string, context: any) => Promise<void>
): Promise<void> {
  console.log('[Renderer] Action triggered:', actionId, context);
  
  if (onAction) {
    await onAction(actionId, context);
  } else {
    // Use default action handler
    await executeAction(actionId, context);
  }
}

/**
 * Extract form data from form event
 */
function extractFormData(event: any): Record<string, any> {
  const formData: Record<string, any> = {};
  
  if (event?.target) {
    const form = event.target as HTMLFormElement;
    const formDataObj = new FormData(form);
    
    formDataObj.forEach((value, key) => {
      formData[key] = value;
    });
  }
  
  return formData;
}

// ============================================================================
// Export utilities for external use
// ============================================================================

export { componentRegistry } from './registry';
export * from './components/layout';
export * from './components/typography';
export * from './components/ui-elements';
export * from './components/forms';
export * from './components/interactive';
export * from './components/advanced-interactive';
export * from './components/data-display';
export * from './components/navigation';
export * from './components/icons';
