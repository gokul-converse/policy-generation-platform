/**
 * Icon Component with Support for Emoji and SVG Icons
 */

'use client';

import React from 'react';

export interface IconProps {
  name: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  color?: string;
  className?: string;
}

export const Icon: React.FC<IconProps> = ({
  name,
  size = 'md',
  color,
  className = '',
}) => {
  const sizeClasses = {
    xs: 'text-sm',
    sm: 'text-base',
    md: 'text-xl',
    lg: 'text-2xl',
    xl: 'text-3xl',
    '2xl': 'text-4xl',
  };

  const style = color ? { color } : {};

  // Support emoji icons directly
  return (
    <span
      className={`inline-flex items-center justify-center ${sizeClasses[size]} ${className}`}
      style={style}
      role="img"
      aria-label={name}
    >
      {name}
    </span>
  );
};

// Icon library with common icons as emoji
export const IconLibrary = {
  // Navigation
  home: '🏠',
  menu: '☰',
  close: '✕',
  back: '←',
  forward: '→',
  up: '↑',
  down: '↓',
  
  // Actions
  check: '✓',
  checkCircle: '✅',
  cross: '✗',
  plus: '+',
  minus: '−',
  edit: '✏️',
  delete: '🗑️',
  save: '💾',
  search: '🔍',
  filter: '🔽',
  sort: '⇅',
  refresh: '↻',
  download: '⬇️',
  upload: '⬆️',
  
  // Status
  info: 'ℹ️',
  warning: '⚠️',
  error: '❌',
  success: '✅',
  pending: '⏳',
  star: '⭐',
  flag: '🚩',
  
  // Documents & Files
  document: '📄',
  folder: '📁',
  file: '📎',
  image: '🖼️',
  pdf: '📕',
  
  // Communication
  email: '📧',
  message: '💬',
  notification: '🔔',
  phone: '📞',
  
  // Business
  chart: '📊',
  trending: '📈',
  money: '💰',
  calendar: '📅',
  clock: '🕐',
  briefcase: '💼',
  building: '🏢',
  
  // People
  user: '👤',
  users: '👥',
  team: '👨‍👩‍👧‍👦',
  admin: '👨‍💼',
  
  // Misc
  settings: '⚙️',
  lock: '🔒',
  unlock: '🔓',
  key: '🔑',
  tag: '🏷️',
  bookmark: '🔖',
  link: '🔗',
  globe: '🌐',
  location: '📍',
  heart: '❤️',
  lightbulb: '💡',
  rocket: '🚀',
  trophy: '🏆',
};
