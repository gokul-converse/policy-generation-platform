/**
 * Data Display Components
 */

'use client';

import React from 'react';
import {
  TableProps,
  ListProps,
  MetricsProps,
  ProgressProps,
} from '@/types/ui-schema';

export const Table: React.FC<TableProps> = ({
  columns,
  data,
  striped = false,
  hoverable = true,
  compact = false,
  className = '',
}) => {
  const rows = typeof data === 'string' ? [] : data; // In real implementation, would resolve binding

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            {columns.map((column) => (
              <th
                key={column.key}
                style={{ width: column.width }}
                className={`${compact ? 'px-3 py-2' : 'px-4 py-3'} text-left text-sm font-semibold text-gray-900 dark:text-gray-100 ${
                  column.align === 'center'
                    ? 'text-center'
                    : column.align === 'right'
                    ? 'text-right'
                    : ''
                }`}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className={`border-b border-gray-200 dark:border-gray-700 ${
                striped && rowIndex % 2 === 1 ? 'bg-gray-50 dark:bg-gray-900' : ''
              } ${hoverable ? 'hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors' : ''}`}
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`${compact ? 'px-3 py-2' : 'px-4 py-3'} text-sm text-gray-700 dark:text-gray-300 ${
                    column.align === 'center'
                      ? 'text-center'
                      : column.align === 'right'
                      ? 'text-right'
                      : ''
                  }`}
                >
                  {row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export const List: React.FC<ListProps & { renderChild?: (child: any) => React.ReactNode }> = ({
  items,
  variant = 'plain',
  spacing = 2,
  className = '',
  renderChild,
}) => {
  const ListTag = variant === 'numbered' ? 'ol' : 'ul';

  const variantClasses = {
    plain: '',
    bullet: 'list-disc list-inside',
    numbered: 'list-decimal list-inside',
    icon: '',
  };

  return (
    <ListTag className={`space-y-${spacing} ${variantClasses[variant]} ${className}`}>
      {items.map((item, index) => {
        // Handle both string arrays and object arrays
        if (typeof item === 'string') {
          return (
            <li key={index} className="text-gray-700 dark:text-gray-300">
              {item}
            </li>
          );
        }
        
        // Handle object format with id and content
        return (
          <li key={item.id || index} className="text-gray-700 dark:text-gray-300">
          {typeof item.content === 'string'
            ? item.content
            : renderChild
            ? renderChild(item.content)
            : null}
        </li>
        );
      })}
    </ListTag>
  );
};

export const Metrics: React.FC<MetricsProps> = ({
  items,
  columns = 3,
  className = '',
}) => {
  const cols = typeof columns === 'number' ? columns : columns?.base || 3;

  return (
    <div
      className={`grid gap-4 ${className}`}
      style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
    >
      {items.map((item, index) => (
        <div
          key={index}
          className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 shadow-sm"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{item.label}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">{item.value}</p>
            </div>
            {item.icon && (
              <div className="text-gray-400 dark:text-gray-600">{item.icon}</div>
            )}
          </div>
          {item.trend && (
            <div className="mt-2 flex items-center gap-1">
              <span
                className={`text-xs font-medium ${
                  item.trend === 'up'
                    ? 'text-green-600 dark:text-green-400'
                    : item.trend === 'down'
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-gray-600 dark:text-gray-400'
                }`}
              >
                {item.trend === 'up' ? '↑' : item.trend === 'down' ? '↓' : '→'}
                {item.trendValue && ` ${item.trendValue}`}
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export const Progress: React.FC<ProgressProps> = ({
  value,
  max = 100,
  label,
  showValue = true,
  variant = 'primary',
  size = 'md',
  className = '',
}) => {
  const percentage = Math.min((value / max) * 100, 100);

  const variantClasses = {
    primary: 'bg-blue-600',
    secondary: 'bg-gray-600',
    success: 'bg-green-600',
    danger: 'bg-red-600',
    warning: 'bg-yellow-600',
    info: 'bg-cyan-600',
    default: 'bg-blue-600',
    muted: 'bg-gray-400',
  };

  const sizeClasses = {
    xs: 'h-1',
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4',
    xl: 'h-5',
  };

  return (
    <div className={className}>
      {(label || showValue) && (
        <div className="flex items-center justify-between mb-2">
          {label && (
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
          )}
          {showValue && (
            <span className="text-sm text-gray-500 dark:text-gray-400">{Math.round(percentage)}%</span>
          )}
        </div>
      )}
      <div className={`w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden ${sizeClasses[size]}`}>
        <div
          className={`${variantClasses[variant]} ${sizeClasses[size]} rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

export const Chart: React.FC<{
  type: 'line' | 'bar' | 'pie' | 'donut';
  data: any;
  title?: string;
  height?: number;
  className?: string;
}> = ({ type, title, height = 300, className = '' }) => {
  // Placeholder - would integrate with a chart library like recharts
  return (
    <div
      className={`bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 ${className}`}
      style={{ height: `${height}px` }}
    >
      {title && <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">{title}</h4>}
      <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-600">
        {type.toUpperCase()} Chart Placeholder
        <br />
        <span className="text-sm">(Integrate with charting library)</span>
      </div>
    </div>
  );
};
