/**
 * Theme Provider for UI Renderer
 * Manages theme configuration from JSON schema
 */

'use client';

import React, { createContext, useContext, useMemo } from 'react';
import { ThemeConfig } from '@/types/ui-schema';

interface ThemeContextValue {
  theme: ThemeConfig;
  cssVariables: Record<string, string>;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

const defaultTheme: ThemeConfig = {
  primary: '#3b82f6',
  secondary: '#6366f1',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#06b6d4',
  background: '#ffffff',
  surface: '#f9fafb',
  text: '#111827',
  textSecondary: '#6b7280',
  border: '#e5e7eb',
  mode: 'light',
};

export const ThemeProvider: React.FC<{
  theme?: ThemeConfig;
  children: React.ReactNode;
}> = ({ theme: providedTheme, children }) => {
  const theme = useMemo(
    () => ({ ...defaultTheme, ...providedTheme }),
    [providedTheme]
  );

  const cssVariables = useMemo(
    () => ({
      '--theme-primary': theme.primary || defaultTheme.primary!,
      '--theme-secondary': theme.secondary || defaultTheme.secondary!,
      '--theme-success': theme.success || defaultTheme.success!,
      '--theme-warning': theme.warning || defaultTheme.warning!,
      '--theme-danger': theme.danger || defaultTheme.danger!,
      '--theme-info': theme.info || defaultTheme.info!,
      '--theme-background': theme.background || defaultTheme.background!,
      '--theme-surface': theme.surface || defaultTheme.surface!,
      '--theme-text': theme.text || defaultTheme.text!,
      '--theme-text-secondary': theme.textSecondary || defaultTheme.textSecondary!,
      '--theme-border': theme.border || defaultTheme.border!,
    }),
    [theme]
  );

  return (
    <ThemeContext.Provider value={{ theme, cssVariables }}>
      <div
        className={`ui-renderer-theme ${theme.mode === 'dark' ? 'dark' : ''}`}
        style={cssVariables as React.CSSProperties}
      >
        {children}
      </div>
    </ThemeContext.Provider>
  );
};

/**
 * Apply theme colors to variant classes
 */
export function getThemedColor(variant: string, theme: ThemeConfig): string {
  switch (variant) {
    case 'primary':
      return theme.primary || defaultTheme.primary!;
    case 'secondary':
      return theme.secondary || defaultTheme.secondary!;
    case 'success':
      return theme.success || defaultTheme.success!;
    case 'warning':
      return theme.warning || defaultTheme.warning!;
    case 'danger':
    case 'error':
      return theme.danger || defaultTheme.danger!;
    case 'info':
      return theme.info || defaultTheme.info!;
    default:
      return theme.text || defaultTheme.text!;
  }
}

/**
 * Get theme-aware background color
 */
export function getThemedBackground(theme: ThemeConfig): string {
  return theme.background || defaultTheme.background!;
}

/**
 * Get theme-aware surface color
 */
export function getThemedSurface(theme: ThemeConfig): string {
  return theme.surface || defaultTheme.surface!;
}

/**
 * Get theme-aware text color
 */
export function getThemedText(theme: ThemeConfig, secondary = false): string {
  return secondary
    ? theme.textSecondary || defaultTheme.textSecondary!
    : theme.text || defaultTheme.text!;
}

/**
 * Get theme-aware border color
 */
export function getThemedBorder(theme: ThemeConfig): string {
  return theme.border || defaultTheme.border!;
}
