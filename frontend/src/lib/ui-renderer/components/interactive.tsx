/**
 * Interactive Components
 */

'use client';

import React from 'react';
import { AccordionProps, TabsProps } from '@/types/ui-schema';

export const Accordion: React.FC<AccordionProps & { renderChild?: (child: any) => React.ReactNode }> = ({
  items,
  allowMultiple = false,
  defaultOpen = [],
  className = '',
  renderChild,
}) => {
  const [openItems, setOpenItems] = React.useState<Set<string>>(new Set(defaultOpen));

  const toggleItem = (id: string) => {
    setOpenItems((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (!allowMultiple) {
          next.clear();
        }
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {items.map((item) => {
        const isOpen = openItems.has(item.id);
        return (
          <div key={item.id} className="border border-gray-200 dark:border-gray-700 rounded-lg">
            <button
              onClick={() => toggleItem(item.id)}
              className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors rounded-lg"
            >
              <span className="font-medium text-gray-900 dark:text-gray-100">{item.title}</span>
              <span className="text-gray-500 dark:text-gray-400 transition-transform" style={{
                transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
              }}>
                ▼
              </span>
            </button>
            {isOpen && (
              <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
                {Array.isArray(item.content)
                  ? item.content.map((child, idx) =>
                      renderChild ? (
                        <div key={idx}>{renderChild(child)}</div>
                      ) : null
                    )
                  : renderChild
                  ? renderChild(item.content)
                  : null}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export const Tabs: React.FC<TabsProps & { renderChild?: (child: any) => React.ReactNode }> = ({
  items,
  defaultTab,
  variant = 'line',
  className = '',
  renderChild,
}) => {
  const [activeTab, setActiveTab] = React.useState(defaultTab || items[0]?.id);

  const variantClasses = {
    line: 'border-b-2',
    enclosed: 'border rounded-t-lg',
    soft: 'bg-gray-100 dark:bg-gray-800 rounded-lg',
  };

  const activeItem = items.find((item) => item.id === activeTab);

  return (
    <div className={className}>
      <div className={`flex gap-2 ${variant === 'line' ? 'border-b border-gray-200 dark:border-gray-700' : ''}`}>
        {items.map((item) => {
          const isActive = item.id === activeTab;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`px-4 py-2 font-medium transition-colors ${
                variant === 'line'
                  ? isActive
                    ? 'border-b-2 border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                  : variant === 'enclosed'
                  ? isActive
                    ? 'border border-b-0 rounded-t-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                  : isActive
                  ? 'bg-white dark:bg-gray-700 rounded-lg text-gray-900 dark:text-gray-100'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      <div className="mt-4">
        {activeItem &&
          (Array.isArray(activeItem.content)
            ? activeItem.content.map((child, idx) =>
                renderChild ? (
                  <div key={idx}>{renderChild(child)}</div>
                ) : null
              )
            : renderChild
            ? renderChild(activeItem.content)
            : null)}
      </div>
    </div>
  );
};
