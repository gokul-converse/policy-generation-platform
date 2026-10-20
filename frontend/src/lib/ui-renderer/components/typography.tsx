/**
 * Typography Components
 */

'use client';

import React from 'react';
import { TextProps, HeadingProps, LinkProps } from '@/types/ui-schema';

export const Text: React.FC<TextProps> = ({
  content,
  variant = 'body',
  size = 'md',
  weight = 'normal',
  color,
  align = 'left',
  className = '',
}) => {
  const variantClasses = {
    body: 'text-gray-700 dark:text-gray-300',
    caption: 'text-gray-500 dark:text-gray-400',
    overline: 'text-gray-600 dark:text-gray-400 uppercase tracking-wide',
  };

  const sizeClasses = {
    xs: 'text-xs',
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl',
  };

  const weightClasses = {
    normal: 'font-normal',
    medium: 'font-medium',
    semibold: 'font-semibold',
    bold: 'font-bold',
  };

  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
    justify: 'text-justify',
  };

  return (
    <p
      className={`${variantClasses[variant]} ${sizeClasses[size]} ${weightClasses[weight]} ${alignClasses[align]} ${className}`}
      style={color ? { color } : undefined}
    >
      {content}
    </p>
  );
};

export const Heading: React.FC<HeadingProps> = ({
  content,
  level = 2,
  size,
  weight = 'bold',
  className = '',
}) => {
  const defaultSizeClasses = {
    1: 'text-4xl',
    2: 'text-3xl',
    3: 'text-2xl',
    4: 'text-xl',
    5: 'text-lg',
    6: 'text-base',
  };

  const customSizeClasses = size
    ? {
        xs: 'text-xs',
        sm: 'text-sm',
        md: 'text-base',
        lg: 'text-lg',
        xl: 'text-xl',
      }[size]
    : '';

  const weightClasses = {
    normal: 'font-normal',
    medium: 'font-medium',
    semibold: 'font-semibold',
    bold: 'font-bold',
  };

  const classes = `${
    customSizeClasses || defaultSizeClasses[level]
  } ${weightClasses[weight]} text-gray-900 dark:text-gray-100 ${className}`;

  switch (level) {
    case 1:
      return <h1 className={classes}>{content}</h1>;
    case 2:
      return <h2 className={classes}>{content}</h2>;
    case 3:
      return <h3 className={classes}>{content}</h3>;
    case 4:
      return <h4 className={classes}>{content}</h4>;
    case 5:
      return <h5 className={classes}>{content}</h5>;
    case 6:
      return <h6 className={classes}>{content}</h6>;
    default:
      return <h2 className={classes}>{content}</h2>;
  }
};

export const Paragraph: React.FC<{ content: string; className?: string }> = ({
  content,
  className = '',
}) => {
  return (
    <p className={`text-gray-700 dark:text-gray-300 leading-relaxed ${className}`}>
      {content}
    </p>
  );
};

export const Link: React.FC<LinkProps> = ({
  href,
  content,
  external = false,
  underline = true,
  className = '',
}) => {
  return (
    <a
      href={href}
      target={external ? '_blank' : undefined}
      rel={external ? 'noopener noreferrer' : undefined}
      className={`text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 ${
        underline ? 'underline' : ''
      } ${className}`}
    >
      {content}
      {external && ' ↗'}
    </a>
  );
};
