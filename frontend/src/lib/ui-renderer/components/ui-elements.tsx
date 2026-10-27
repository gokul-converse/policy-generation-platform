/**
 * UI Elements Components
 */

'use client';

import React from 'react';
import { Button as BaseButton } from '@/components/ui/button';
import { Card as BaseCard, CardHeader as BaseCardHeader, CardBody as BaseCardBody } from '@/components/ui/card';
import {
  ButtonProps,
  BadgeProps,
  AlertProps,
  CardProps,
  DividerProps,
  ImageProps,
} from '@/types/ui-schema';

export const Button: React.FC<ButtonProps & { children?: React.ReactNode }> = ({
  label,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  fullWidth = false,
  onClick,
  className = '',
  children,
}) => {
  // Map size variant to Button component size
  const mappedSize = size === 'xs' ? 'sm' : size === 'xl' ? 'lg' : size;

  return (
    <BaseButton
      variant={variant}
      size={mappedSize as 'sm' | 'md' | 'lg'}
      disabled={disabled}
      loading={loading}
      className={`${fullWidth ? 'w-full' : ''} ${className}`}
    >
      {children || label}
    </BaseButton>
  );
};

export const Badge: React.FC<BadgeProps> = ({
  label,
  variant = 'default',
  size = 'md',
  rounded = true,
  className = '',
}) => {
  const variantClasses = {
    primary: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    secondary: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    danger: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    info: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
    default: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200',
    muted: 'bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  };

  const sizeClasses = {
    xs: 'text-xs px-2 py-0.5',
    sm: 'text-xs px-2.5 py-0.5',
    md: 'text-sm px-3 py-1',
    lg: 'text-base px-3.5 py-1.5',
    xl: 'text-lg px-4 py-2',
  };

  return (
    <span
      className={`inline-flex items-center font-medium ${rounded ? 'rounded-full' : 'rounded'} ${
        variantClasses[variant]
      } ${sizeClasses[size]} ${className}`}
    >
      {label}
    </span>
  );
};

export const Alert: React.FC<AlertProps> = ({
  message,
  title,
  variant = 'info',
  dismissible = false,
  className = '',
}) => {
  const [dismissed, setDismissed] = React.useState(false);

  if (dismissed) return null;

  const variantClasses = {
    info: 'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-200',
    success: 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-200',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-200',
    error: 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-200',
  };

  return (
    <div className={`p-4 rounded-lg border ${variantClasses[variant]} ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {title && <h4 className="font-semibold mb-1">{title}</h4>}
          <p className="text-sm">{message}</p>
        </div>
        {dismissible && (
          <button
            onClick={() => setDismissed(true)}
            className="ml-4 text-current opacity-50 hover:opacity-100 transition-opacity"
            aria-label="Dismiss"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
};

export const Card: React.FC<CardProps & { children?: React.ReactNode }> = ({
  title,
  subtitle,
  variant = 'default',
  hoverable = false,
  padding = 6,
  className = '',
  children,
}) => {
  const variantClasses = {
    default: 'bg-white dark:bg-gray-800 shadow-sm',
    bordered: 'bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700',
    elevated: 'bg-white dark:bg-gray-800 shadow-lg',
  };

  return (
    <BaseCard className={`${variantClasses[variant]} ${className}`} hoverable={hoverable}>
      {(title || subtitle) && <BaseCardHeader title={title || ''} subtitle={subtitle} />}
      <BaseCardBody className={`p-${padding}`}>{children}</BaseCardBody>
    </BaseCard>
  );
};

export const Divider: React.FC<DividerProps> = ({
  orientation = 'horizontal',
  variant = 'solid',
  className = '',
}) => {
  const variantClasses = {
    solid: 'border-solid',
    dashed: 'border-dashed',
    dotted: 'border-dotted',
  };

  if (orientation === 'vertical') {
    return (
      <div
        className={`border-l ${variantClasses[variant]} border-gray-200 dark:border-gray-700 h-full ${className}`}
      />
    );
  }

  return (
    <hr
      className={`border-t ${variantClasses[variant]} border-gray-200 dark:border-gray-700 ${className}`}
    />
  );
};

export const Image: React.FC<ImageProps> = ({
  src,
  alt,
  width,
  height,
  rounded = false,
  objectFit = 'cover',
  className = '',
}) => {
  const style: React.CSSProperties = {
    width: width ? `${width}px` : '100%',
    height: height ? `${height}px` : 'auto',
    objectFit,
  };

  return (
    <img
      src={src}
      alt={alt}
      style={style}
      className={`${rounded ? 'rounded-lg' : ''} ${className}`}
    />
  );
};
