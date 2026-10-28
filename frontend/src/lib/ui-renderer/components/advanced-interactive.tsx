/**
 * Advanced Interactive Components
 * Modal, Dropdown, Tooltip, Stepper, etc.
 */

'use client';

import React from 'react';

export const Modal: React.FC<{
  isOpen?: boolean;
  title?: string;
  onClose?: () => void;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  className?: string;
  children?: React.ReactNode;
}> = ({ isOpen = true, title, onClose, size = 'md', className = '', children }) => {
  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-full mx-4',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50">
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-xl ${sizeClasses[size]} w-full ${className}`}>
        {title && (
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
            {onClose && (
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-xl"
              >
                ✕
              </button>
            )}
          </div>
        )}
        <div className="px-6 py-4">{children}</div>
      </div>
    </div>
  );
};

export const Dropdown: React.FC<{
  trigger: string;
  items: Array<{ label: string; value: string; icon?: string; onClick?: string }>;
  className?: string;
}> = ({ trigger, items, className = '' }) => {
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
      >
        {trigger}
        <span className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}>▼</span>
      </button>
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20">
            {items.map((item, idx) => (
              <button
                key={idx}
                className="w-full px-4 py-2 text-left text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors first:rounded-t-lg last:rounded-b-lg flex items-center gap-2"
                onClick={() => {
                  setIsOpen(false);
                }}
              >
                {item.icon && <span>{item.icon}</span>}
                {item.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export const Tooltip: React.FC<{
  content: string;
  position?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
  children?: React.ReactNode;
}> = ({ content, position = 'top', className = '', children }) => {
  const [isVisible, setIsVisible] = React.useState(false);

  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  return (
    <div
      className={`relative inline-block ${className}`}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div
          className={`absolute z-50 px-3 py-2 text-sm text-white bg-gray-900 dark:bg-gray-700 rounded-lg shadow-lg whitespace-nowrap ${positionClasses[position]}`}
        >
          {content}
        </div>
      )}
    </div>
  );
};

export const Stepper: React.FC<{
  steps: Array<{ id: string; label: string; description?: string; status?: 'complete' | 'current' | 'upcoming' }>;
  currentStep?: string;
  orientation?: 'horizontal' | 'vertical';
  className?: string;
}> = ({ steps, currentStep, orientation = 'horizontal', className = '' }) => {
  const getCurrentIndex = () => {
    if (currentStep) {
      return steps.findIndex(step => step.id === currentStep);
    }
    return steps.findIndex(step => step.status === 'current');
  };

  const currentIndex = getCurrentIndex();

  return (
    <div className={`${orientation === 'horizontal' ? 'flex' : 'space-y-4'} ${className}`}>
      {steps.map((step, index) => {
        const status = step.status || (index < currentIndex ? 'complete' : index === currentIndex ? 'current' : 'upcoming');
        const isLast = index === steps.length - 1;

        return (
          <div
            key={step.id}
            className={`${orientation === 'horizontal' ? 'flex-1' : ''} flex ${orientation === 'horizontal' ? 'items-center' : 'items-start'}`}
          >
            <div className={`flex ${orientation === 'horizontal' ? 'flex-col items-center flex-1' : 'flex-row items-start'}`}>
              <div className="flex items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                    status === 'complete'
                      ? 'bg-green-600 text-white'
                      : status === 'current'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                  }`}
                >
                  {status === 'complete' ? '✓' : index + 1}
                </div>
                {orientation === 'horizontal' && !isLast && (
                  <div
                    className={`flex-1 h-1 mx-2 ${
                      status === 'complete' ? 'bg-green-600' : 'bg-gray-200 dark:bg-gray-700'
                    }`}
                    style={{ minWidth: '40px' }}
                  />
                )}
              </div>
              <div className={`${orientation === 'horizontal' ? 'text-center mt-2' : 'ml-4'}`}>
                <div
                  className={`font-medium ${
                    status === 'current'
                      ? 'text-blue-600 dark:text-blue-400'
                      : status === 'complete'
                      ? 'text-gray-900 dark:text-gray-100'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}
                >
                  {step.label}
                </div>
                {step.description && (
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">{step.description}</div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export const Timeline: React.FC<{
  items: Array<{
    id: string;
    title: string;
    description?: string;
    date?: string;
    icon?: string;
    variant?: 'success' | 'warning' | 'error' | 'info' | 'default';
  }>;
  className?: string;
}> = ({ items, className = '' }) => {
  return (
    <div className={`space-y-6 ${className}`}>
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        const variantColors = {
          success: 'bg-green-600',
          warning: 'bg-yellow-600',
          error: 'bg-red-600',
          info: 'bg-blue-600',
          default: 'bg-gray-600',
        };

        return (
          <div key={item.id} className="flex items-start">
            <div className="flex flex-col items-center mr-4">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  variantColors[item.variant || 'default']
                } text-white font-semibold`}
              >
                {item.icon || (index + 1)}
              </div>
              {!isLast && (
                <div className="w-0.5 h-full bg-gray-200 dark:bg-gray-700 mt-2" style={{ minHeight: '40px' }} />
              )}
            </div>
            <div className="flex-1 pb-6">
              {item.date && (
                <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">{item.date}</div>
              )}
              <div className="font-semibold text-gray-900 dark:text-gray-100">{item.title}</div>
              {item.description && (
                <div className="text-gray-600 dark:text-gray-400 mt-1">{item.description}</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export const StatCard: React.FC<{
  label: string;
  value: string | number;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: string;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger';
  className?: string;
}> = ({ label, value, change, trend, icon, variant = 'default', className = '' }) => {
  const variantClasses = {
    default: 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700',
    primary: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    success: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
    warning: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
    danger: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
  };

  return (
    <div className={`p-6 border rounded-lg ${variantClasses[variant]} ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{label}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2">{value}</p>
          {change && (
            <div className="flex items-center mt-2">
              <span
                className={`text-sm font-medium ${
                  trend === 'up'
                    ? 'text-green-600 dark:text-green-400'
                    : trend === 'down'
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-gray-600 dark:text-gray-400'
                }`}
              >
                {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {change}
              </span>
            </div>
          )}
        </div>
        {icon && (
          <div className="text-3xl opacity-50">{icon}</div>
        )}
      </div>
    </div>
  );
};

export const InfoCard: React.FC<{
  title?: string;
  icon?: string;
  iconColor?: string;
  children?: React.ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info';
  className?: string;
}> = ({ title, icon, iconColor, children, variant = 'default', className = '' }) => {
  const variantClasses = {
    default: 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700',
    primary: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    success: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
    warning: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
    danger: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    info: 'bg-cyan-50 dark:bg-cyan-900/20 border-cyan-200 dark:border-cyan-800',
  };

  return (
    <div className={`p-4 border rounded-lg ${variantClasses[variant]} ${className}`}>
      <div className="flex items-start gap-3">
        {icon && (
          <div className={`text-2xl ${iconColor || 'text-gray-600'}`}>{icon}</div>
        )}
        <div className="flex-1">
          {title && (
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">{title}</h4>
          )}
          <div className="text-gray-700 dark:text-gray-300">{children}</div>
        </div>
      </div>
    </div>
  );
};
