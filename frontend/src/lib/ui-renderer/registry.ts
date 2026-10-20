/**
 * Component Registry
 * Central registry for mapping component types to React components
 */

import React from 'react';
import { ComponentType } from '@/types/ui-schema';

export type ComponentRenderer = React.FC<any>;

class ComponentRegistry {
  private components: Map<ComponentType, ComponentRenderer> = new Map();

  /**
   * Register a component renderer
   */
  register(type: ComponentType, component: ComponentRenderer): void {
    this.components.set(type, component);
  }

  /**
   * Register multiple component renderers
   */
  registerMany(components: Record<string, ComponentRenderer>): void {
    Object.entries(components).forEach(([type, component]) => {
      this.register(type as ComponentType, component);
    });
  }

  /**
   * Get a component renderer by type
   */
  get(type: ComponentType): ComponentRenderer | undefined {
    return this.components.get(type);
  }

  /**
   * Check if a component type is registered
   */
  has(type: ComponentType): boolean {
    return this.components.has(type);
  }

  /**
   * Get all registered component types
   */
  getRegisteredTypes(): ComponentType[] {
    return Array.from(this.components.keys());
  }

  /**
   * Unregister a component
   */
  unregister(type: ComponentType): void {
    this.components.delete(type);
  }

  /**
   * Clear all registered components
   */
  clear(): void {
    this.components.clear();
  }
}

// Singleton instance
export const componentRegistry = new ComponentRegistry();
