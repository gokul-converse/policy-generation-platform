/**
 * Action Handler System
 * Manages actions triggered by UI components (onClick, onSubmit, etc.)
 * Designed for future API integration
 */

export type ActionType = 'navigate' | 'api' | 'setState' | 'submit' | 'custom' | 'log';

export interface ActionContext {
  /** Component that triggered the action */
  componentId?: string;
  /** Form data if action is from a form */
  formData?: Record<string, any>;
  /** Current UI state */
  state?: Record<string, any>;
  /** Additional metadata */
  metadata?: Record<string, any>;
}

export interface ActionDefinition {
  id: string;
  type: ActionType;
  config: ActionConfig;
}

export interface ActionConfig {
  /** For 'navigate' type */
  url?: string;
  openInNewTab?: boolean;
  
  /** For 'api' type */
  endpoint?: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: Record<string, any>;
  onSuccess?: string; // Action ID to trigger on success
  onError?: string; // Action ID to trigger on error
  
  /** For 'setState' type */
  stateKey?: string;
  stateValue?: any;
  
  /** For 'submit' type */
  target?: string;
  validation?: boolean;
  
  /** For 'custom' type */
  handler?: string;
  params?: Record<string, any>;
  
  /** General */
  label?: string;
  description?: string;
}

export interface ActionResult {
  success: boolean;
  data?: any;
  error?: string;
  nextAction?: string;
}

/**
 * Action Registry
 * Maps action IDs to their definitions
 */
class ActionRegistry {
  private actions: Map<string, ActionDefinition> = new Map();
  private handlers: Map<string, (context: ActionContext) => Promise<ActionResult>> = new Map();

  register(action: ActionDefinition): void {
    this.actions.set(action.id, action);
  }

  registerHandler(
    handlerName: string,
    handler: (context: ActionContext) => Promise<ActionResult>
  ): void {
    this.handlers.set(handlerName, handler);
  }

  get(actionId: string): ActionDefinition | undefined {
    return this.actions.get(actionId);
  }

  getHandler(handlerName: string): ((context: ActionContext) => Promise<ActionResult>) | undefined {
    return this.handlers.get(handlerName);
  }

  clear(): void {
    this.actions.clear();
  }
}

export const actionRegistry = new ActionRegistry();

/**
 * Execute an action
 */
export async function executeAction(
  actionId: string,
  context: ActionContext = {}
): Promise<ActionResult> {
  const action = actionRegistry.get(actionId);

  if (!action) {
    console.warn(`Action not found: ${actionId}`);
    return {
      success: false,
      error: `Action not found: ${actionId}`,
    };
  }

  console.log(`[Action] Executing: ${actionId}`, { type: action.type, context });

  try {
    switch (action.type) {
      case 'navigate':
        return await handleNavigate(action.config, context);
      
      case 'api':
        return await handleApiCall(action.config, context);
      
      case 'setState':
        return await handleSetState(action.config, context);
      
      case 'submit':
        return await handleSubmit(action.config, context);
      
      case 'custom':
        return await handleCustom(action.config, context);
      
      case 'log':
        return await handleLog(action.config, context);
      
      default:
        console.warn(`Unknown action type: ${action.type}`);
        return {
          success: false,
          error: `Unknown action type: ${action.type}`,
        };
    }
  } catch (error) {
    console.error(`[Action] Error executing ${actionId}:`, error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Navigate to a URL
 */
async function handleNavigate(config: ActionConfig, context: ActionContext): Promise<ActionResult> {
  const { url, openInNewTab } = config;

  if (!url) {
    return { success: false, error: 'No URL provided' };
  }

  console.log(`[Navigate] ${openInNewTab ? 'Opening in new tab' : 'Navigating to'}: ${url}`);

  if (openInNewTab) {
    window.open(url, '_blank', 'noopener,noreferrer');
  } else {
    window.location.href = url;
  }

  return { success: true, data: { url } };
}

/**
 * Make an API call
 * TODO: Implement with actual API client when backend is ready
 */
async function handleApiCall(config: ActionConfig, context: ActionContext): Promise<ActionResult> {
  const { endpoint, method = 'POST', headers = {}, body } = config;

  if (!endpoint) {
    return { success: false, error: 'No endpoint provided' };
  }

  console.log(`[API Call] ${method} ${endpoint}`, { body, formData: context.formData });

  // For now, simulate API call
  // TODO: Replace with actual API client
  await new Promise((resolve) => setTimeout(resolve, 1000));

  // Mock response
  const mockResponse = {
    id: `mock-${Date.now()}`,
    ...body,
    ...context.formData,
    timestamp: new Date().toISOString(),
  };

  console.log(`[API Call] Success:`, mockResponse);

  return {
    success: true,
    data: mockResponse,
    nextAction: config.onSuccess,
  };
}

/**
 * Update state
 * TODO: Integrate with state management solution
 */
async function handleSetState(config: ActionConfig, context: ActionContext): Promise<ActionResult> {
  const { stateKey, stateValue } = config;

  if (!stateKey) {
    return { success: false, error: 'No state key provided' };
  }

  console.log(`[SetState] ${stateKey} =`, stateValue);

  // For now, just log
  // TODO: Integrate with state management (Zustand, Redux, etc.)

  return {
    success: true,
    data: { [stateKey]: stateValue },
  };
}

/**
 * Submit form
 */
async function handleSubmit(config: ActionConfig, context: ActionContext): Promise<ActionResult> {
  const { target, validation = true } = config;

  console.log(`[Submit] Form submission`, { target, formData: context.formData });

  // Basic validation check
  if (validation && context.formData) {
    const requiredFields = Object.keys(context.formData).filter((key) => key.includes('required'));
    const missingFields = requiredFields.filter((field) => !context.formData![field]);

    if (missingFields.length > 0) {
      return {
        success: false,
        error: `Missing required fields: ${missingFields.join(', ')}`,
      };
    }
  }

  // If target is an API endpoint, delegate to API handler
  if (target && target.startsWith('/api/')) {
    return handleApiCall(
      {
        endpoint: target,
        method: 'POST',
        body: context.formData,
      },
      context
    );
  }

  return {
    success: true,
    data: context.formData,
  };
}

/**
 * Execute custom handler
 */
async function handleCustom(config: ActionConfig, context: ActionContext): Promise<ActionResult> {
  const { handler, params } = config;

  if (!handler) {
    return { success: false, error: 'No handler provided' };
  }

  console.log(`[Custom] Executing handler: ${handler}`, params);

  const customHandler = actionRegistry.getHandler(handler);

  if (!customHandler) {
    console.warn(`Custom handler not found: ${handler}`);
    return {
      success: false,
      error: `Handler not found: ${handler}`,
    };
  }

  return await customHandler({ ...context, metadata: { ...context.metadata, ...params } });
}

/**
 * Log action
 */
async function handleLog(config: ActionConfig, context: ActionContext): Promise<ActionResult> {
  console.log(`[Log]`, config, context);
  return { success: true };
}

/**
 * Batch execute multiple actions
 */
export async function executeActions(
  actionIds: string[],
  context: ActionContext = {}
): Promise<ActionResult[]> {
  const results: ActionResult[] = [];

  for (const actionId of actionIds) {
    const result = await executeAction(actionId, context);
    results.push(result);

    // If action failed and we should stop, break
    if (!result.success) {
      console.warn(`Action chain stopped at: ${actionId}`);
      break;
    }

    // If action specifies next action, execute it
    if (result.nextAction) {
      const nextResult = await executeAction(result.nextAction, {
        ...context,
        metadata: { ...context.metadata, previousResult: result.data },
      });
      results.push(nextResult);
    }
  }

  return results;
}

/**
 * Register default handlers
 */
export function registerDefaultHandlers(): void {
  // Policy generation handler
  actionRegistry.registerHandler('generatePolicy', async (context) => {
    console.log('[Handler] Generate Policy', context.formData);
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000));
    
    return {
      success: true,
      data: {
        policyId: `policy-${Date.now()}`,
        status: 'generated',
        paragraphs: [
          { id: '1', content: 'Policy section 1...', order: 1 },
          { id: '2', content: 'Policy section 2...', order: 2 },
        ],
      },
    };
  });

  // UI generation handler
  actionRegistry.registerHandler('generateUI', async (context) => {
    console.log('[Handler] Generate UI', context);
    
    await new Promise((resolve) => setTimeout(resolve, 1500));
    
    return {
      success: true,
      data: {
        uiId: `ui-${Date.now()}`,
        components: [],
      },
    };
  });

  // Generic form submit handler
  actionRegistry.registerHandler('submitForm', async (context) => {
    console.log('[Handler] Submit Form', context.formData);
    
    await new Promise((resolve) => setTimeout(resolve, 1000));
    
    return {
      success: true,
      data: {
        submittedAt: new Date().toISOString(),
        ...context.formData,
      },
    };
  });
}

// Initialize default handlers
registerDefaultHandlers();
