/**
 * Layout Components
 */

'use client';

import React from 'react';
import {
  ContainerProps,
  GridProps,
  RowProps,
  ColumnProps,
  StackProps,
} from '@/types/ui-schema';

export const Container: React.FC<ContainerProps & { children?: React.ReactNode }> = ({
  maxWidth = 'lg',
  padding = 4,
  centered = false,
  className = '',
  children,
}) => {
  const maxWidthClasses = {
    sm: 'max-w-screen-sm',
    md: 'max-w-screen-md',
    lg: 'max-w-screen-lg',
    xl: 'max-w-screen-xl',
    full: 'max-w-full',
  };

  const paddingValue = typeof padding === 'number' ? padding : padding?.base || 4;

  return (
    <div
      className={`${maxWidthClasses[maxWidth]} ${centered ? 'mx-auto' : ''} p-${paddingValue} ${className}`}
    >
      {children}
    </div>
  );
};

export const Grid: React.FC<GridProps & { children?: React.ReactNode }> = ({
  columns = 2,
  gap = 4,
  alignItems = 'stretch',
  className = '',
  children,
}) => {
  const cols = typeof columns === 'number' ? columns : columns?.base || 2;
  
  const alignClasses = {
    start: 'items-start',
    center: 'items-center',
    end: 'items-end',
    stretch: 'items-stretch',
  };

  return (
    <div
      className={`grid gap-${gap} ${alignClasses[alignItems]} ${className}`}
      style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
    >
      {children}
    </div>
  );
};

export const Row: React.FC<RowProps & { children?: React.ReactNode }> = ({
  gap = 4,
  justify = 'start',
  align = 'start',
  wrap = false,
  className = '',
  children,
}) => {
  const justifyClasses = {
    start: 'justify-start',
    center: 'justify-center',
    end: 'justify-end',
    between: 'justify-between',
    around: 'justify-around',
  };

  const alignClasses = {
    start: 'items-start',
    center: 'items-center',
    end: 'items-end',
    stretch: 'items-stretch',
  };

  return (
    <div
      className={`flex gap-${gap} ${justifyClasses[justify]} ${alignClasses[align]} ${
        wrap ? 'flex-wrap' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
};

export const Column: React.FC<ColumnProps & { children?: React.ReactNode }> = ({
  span,
  gap = 0,
  className = '',
  children,
}) => {
  const spanValue = typeof span === 'number' ? span : span?.base;
  const spanClass = spanValue ? `col-span-${spanValue}` : '';

  return (
    <div className={`flex flex-col ${gap > 0 ? `gap-${gap}` : ''} ${spanClass} ${className}`}>
      {children}
    </div>
  );
};

export const Stack: React.FC<StackProps & { children?: React.ReactNode }> = ({
  direction = 'vertical',
  gap = 4,
  align = 'stretch',
  className = '',
  children,
}) => {
  const alignClasses = {
    start: direction === 'vertical' ? 'items-start' : 'justify-start',
    center: direction === 'vertical' ? 'items-center' : 'justify-center',
    end: direction === 'vertical' ? 'items-end' : 'justify-end',
    stretch: direction === 'vertical' ? 'items-stretch' : 'justify-stretch',
  };

  return (
    <div
      className={`flex ${
        direction === 'vertical' ? 'flex-col' : 'flex-row'
      } gap-${gap} ${alignClasses[align]} ${className}`}
    >
      {children}
    </div>
  );
};

export const Spacer: React.FC<{ height?: number; width?: number }> = ({
  height,
  width,
}) => {
  const style: React.CSSProperties = {};
  if (height) style.height = `${height}px`;
  if (width) style.width = `${width}px`;
  
  return <div style={style} />;
};
