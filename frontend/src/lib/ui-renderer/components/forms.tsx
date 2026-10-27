/**
 * Form Components
 */

'use client';

import React from 'react';
import {
  FormProps,
  InputProps,
  TextareaProps as TextareaSchemaProps,
  SelectProps,
  CheckboxProps,
  RadioProps,
} from '@/types/ui-schema';

export const Form: React.FC<FormProps & { children?: React.ReactNode }> = ({
  onSubmit,
  validationMode = 'onSubmit',
  className = '',
  children,
}) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // In real implementation, would trigger action with form data
    console.log('Form submitted:', onSubmit);
  };

  return (
    <form onSubmit={handleSubmit} className={`space-y-4 ${className}`}>
      {children}
    </form>
  );
};

export const Input: React.FC<InputProps> = ({
  name,
  label,
  placeholder,
  type = 'text',
  defaultValue,
  required = false,
  disabled = false,
  helperText,
  errorMessage,
  className = '',
}) => {
  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <input
        id={name}
        name={name}
        type={type}
        placeholder={placeholder}
        defaultValue={defaultValue}
        required={required}
        disabled={disabled}
        className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 disabled:opacity-50 disabled:cursor-not-allowed ${
          errorMessage ? 'border-red-500' : ''
        }`}
      />
      {helperText && !errorMessage && (
        <p className="text-xs text-gray-500 dark:text-gray-400">{helperText}</p>
      )}
      {errorMessage && <p className="text-xs text-red-500">{errorMessage}</p>}
    </div>
  );
};

export const Textarea: React.FC<TextareaSchemaProps> = ({
  name,
  label,
  placeholder,
  rows = 4,
  defaultValue,
  required = false,
  disabled = false,
  helperText,
  maxLength,
  className = '',
}) => {
  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <textarea
        id={name}
        name={name}
        placeholder={placeholder}
        rows={rows}
        defaultValue={defaultValue}
        required={required}
        disabled={disabled}
        maxLength={maxLength}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 disabled:opacity-50 disabled:cursor-not-allowed resize-vertical"
      />
      {helperText && (
        <p className="text-xs text-gray-500 dark:text-gray-400">{helperText}</p>
      )}
      {maxLength && (
        <p className="text-xs text-gray-400 dark:text-gray-500 text-right">
          {maxLength} characters max
        </p>
      )}
    </div>
  );
};

export const Select: React.FC<SelectProps> = ({
  name,
  label,
  placeholder,
  options,
  defaultValue,
  required = false,
  disabled = false,
  multiple = false,
  className = '',
}) => {
  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <select
        id={name}
        name={name}
        defaultValue={defaultValue}
        required={required}
        disabled={disabled}
        multiple={multiple}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export const Checkbox: React.FC<CheckboxProps> = ({
  name,
  label,
  defaultChecked = false,
  disabled = false,
  required = false,
  className = '',
}) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <input
        id={name}
        name={name}
        type="checkbox"
        defaultChecked={defaultChecked}
        disabled={disabled}
        required={required}
        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <label
        htmlFor={name}
        className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer select-none"
      >
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
    </div>
  );
};

export const Radio: React.FC<RadioProps> = ({
  name,
  label,
  value,
  defaultChecked = false,
  disabled = false,
  className = '',
}) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <input
        id={`${name}-${value}`}
        name={name}
        type="radio"
        value={value}
        defaultChecked={defaultChecked}
        disabled={disabled}
        className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <label
        htmlFor={`${name}-${value}`}
        className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer select-none"
      >
        {label}
      </label>
    </div>
  );
};

export const Switch: React.FC<{
  name: string;
  label?: string;
  defaultChecked?: boolean;
  disabled?: boolean;
  className?: string;
}> = ({ name, label, defaultChecked = false, disabled = false, className = '' }) => {
  const [checked, setChecked] = React.useState(defaultChecked);

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => setChecked(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
          checked ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
      {label && (
        <label className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer select-none">
          {label}
        </label>
      )}
      <input type="hidden" name={name} value={checked ? 'true' : 'false'} />
    </div>
  );
};
