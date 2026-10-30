/**
 * UI Renderer Component
 * Renders generated UI components from JSON structure
 */

'use client';

import React from 'react';
import { UIComponent } from '@/types';

interface UIRendererProps {
  components: UIComponent[];
}

export const UIRenderer: React.FC<UIRendererProps> = ({ components }) => {
  return (
    <div className="space-y-6">
      {components.map((component, index) => (
        <ComponentRenderer key={index} component={component} />
      ))}
    </div>
  );
};

const ComponentRenderer: React.FC<{ component: UIComponent }> = ({ component }) => {
  switch (component?.type) {
    case 'header':
      return <HeaderComponent {...component.props} />;
    case 'section':
      return <SectionComponent {...component.props} children={component.children} />;
    case 'grid':
      return <GridComponent {...component.props} children={component.children} />;
    case 'card':
      return <CardComponent {...component.props} children={component.children} />;
    case 'text':
      return <TextComponent {...component.props} />;
    case 'badge':
      return <BadgeComponent {...component.props} />;
    case 'metrics':
      return <MetricsComponent {...component.props} />;
    case 'alert':
      return <AlertComponent {...component.props} />;
    default:
      return null;
  }
};

const HeaderComponent: React.FC<any> = ({ title, subtitle, variant }) => (
  <div className={`p-6 rounded-lg ${variant === 'primary' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-800'}`}>
    <h1 className="text-3xl font-bold">{title}</h1>
    {subtitle && <p className="text-lg mt-2 opacity-90">{subtitle}</p>}
  </div>
);

const SectionComponent: React.FC<any> = ({ title, layout, children }) => (
  <div className={`${layout === 'card' ? 'bg-white dark:bg-gray-800 p-6 rounded-lg shadow' : ''}`}>
    {title && <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">{title}</h2>}
    <div className="space-y-3">
      {children?.map((child: UIComponent, index: number) => (
        <ComponentRenderer key={index} component={child} />
      ))}
    </div>
  </div>
);

const GridComponent: React.FC<any> = ({ columns, gap, children }) => (
  <div
    className={`grid gap-${gap || 4}`}
    style={{ gridTemplateColumns: `repeat(${columns || 2}, minmax(0, 1fr))` }}
  >
    {children?.map((child: UIComponent, index: number) => (
      <ComponentRenderer key={index} component={child} />
    ))}
  </div>
);

const CardComponent: React.FC<any> = ({ title, variant, children }) => (
  <div className={`p-4 rounded-lg ${variant === 'bordered' ? 'border-2 border-gray-200 dark:border-gray-700' : 'bg-white dark:bg-gray-800 shadow'}`}>
    {title && <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">{title}</h3>}
    {children?.map((child: UIComponent, index: number) => (
      <ComponentRenderer key={index} component={child} />
    ))}
  </div>
);

const TextComponent: React.FC<any> = ({ content, weight, size }) => {
  const sizeClasses: Record<string, string> = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl',
  };
  
  const weightClasses: Record<string, string> = {
    normal: 'font-normal',
    medium: 'font-medium',
    semibold: 'font-semibold',
    bold: 'font-bold',
  };

  return (
    <p className={`text-gray-700 dark:text-gray-300 ${sizeClasses[size] || 'text-base'} ${weightClasses[weight] || 'font-normal'}`}>
      {content}
    </p>
  );
};

const BadgeComponent: React.FC<any> = ({ label, color }) => {
  const colorClasses: Record<string, string> = {
    green: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    blue: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    red: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    yellow: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  };

  return (
    <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${colorClasses[color] || colorClasses.blue}`}>
      {label}
    </span>
  );
};

const MetricsComponent: React.FC<any> = ({ items }) => (
  <div className="grid grid-cols-3 gap-4">
    {items?.map((item: any, index: number) => (
      <div key={index} className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
        <p className="text-sm text-gray-500 dark:text-gray-400">{item.label}</p>
        <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">{item.value}</p>
        {item.trend && (
          <span className={`text-xs ${
            item.trend === 'up' ? 'text-green-600' :
            item.trend === 'down' ? 'text-red-600' :
            'text-gray-600'
          }`}>
            {item.trend === 'up' ? '↑' : item.trend === 'down' ? '↓' : '—'}
          </span>
        )}
      </div>
    ))}
  </div>
);

const AlertComponent: React.FC<any> = ({ message, variant }) => {
  const variants: Record<string, string> = {
    info: 'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-200',
    success: 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-200',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-200',
    error: 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-200',
  };

  return (
    <div className={`p-4 rounded-lg border ${variants[variant] || variants.info}`}>
      <p className="text-sm">{message}</p>
    </div>
  );
};
