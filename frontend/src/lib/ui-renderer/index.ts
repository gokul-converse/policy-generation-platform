/**
 * JSON UI Renderer
 * Export all public APIs
 */

export { JSONUIRenderer, componentRegistry } from './renderer';
export type { JSONUIRendererProps } from './renderer';

// Export types
export * from '@/types/ui-schema';

// Re-export component registry for custom registrations
export { componentRegistry as registry } from './registry';

// Export action system (specific exports to avoid conflicts)
export {
  executeAction,
  executeActions,
  actionRegistry,
  registerDefaultHandlers,
} from './actions/action-handler';
export type {
  ActionType,
  ActionContext,
  ActionConfig,
  ActionResult,
} from './actions/action-handler';
