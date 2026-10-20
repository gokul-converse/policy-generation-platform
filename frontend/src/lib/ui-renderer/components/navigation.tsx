/**
 * Navigation Components
 */

'use client';

import React from 'react';
import { NavProps, BreadcrumbProps, PaginationProps } from '@/types/ui-schema';

export const Nav: React.FC<NavProps> = ({
  items,
  variant = 'horizontal',
  className = '',
}) => {
  return (
    <nav
      className={`${
        variant === 'horizontal' ? 'flex gap-6' : 'flex flex-col gap-2'
      } ${className}`}
    >
      {items.map((item, index) => (
        <a
          key={index}
          href={item.href}
          className={`${
            item.active
              ? 'text-blue-600 dark:text-blue-400 font-semibold'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
          } transition-colors`}
        >
          {item.icon && <span className="mr-2">{item.icon}</span>}
          {item.label}
        </a>
      ))}
    </nav>
  );
};

export const Breadcrumb: React.FC<BreadcrumbProps> = ({
  items,
  separator = '/',
  className = '',
}) => {
  return (
    <nav className={`flex items-center gap-2 text-sm ${className}`}>
      {items.map((item, index) => (
        <React.Fragment key={index}>
          {index > 0 && (
            <span className="text-gray-400 dark:text-gray-600">{separator}</span>
          )}
          {item.href ? (
            <a
              href={item.href}
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              {item.label}
            </a>
          ) : (
            <span className="text-gray-600 dark:text-gray-400">{item.label}</span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
};

export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  showFirstLast = true,
  className = '',
}) => {
  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      // In real implementation, would trigger action
      console.log('Page change:', page, onPageChange);
    }
  };

  const renderPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      if (currentPage <= 3) {
        pages.push(1, 2, 3, 4, '...', totalPages);
      } else if (currentPage >= totalPages - 2) {
        pages.push(1, '...', totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
      } else {
        pages.push(1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages);
      }
    }

    return pages;
  };

  return (
    <nav className={`flex items-center gap-2 ${className}`}>
      {showFirstLast && (
        <button
          onClick={() => handlePageChange(1)}
          disabled={currentPage === 1}
          className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          First
        </button>
      )}
      <button
        onClick={() => handlePageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Previous
      </button>
      {renderPageNumbers().map((page, index) =>
        typeof page === 'number' ? (
          <button
            key={index}
            onClick={() => handlePageChange(page)}
            className={`px-3 py-2 text-sm font-medium rounded-lg ${
              page === currentPage
                ? 'text-white bg-blue-600 dark:bg-blue-500'
                : 'text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            {page}
          </button>
        ) : (
          <span key={index} className="px-2 text-gray-400">
            {page}
          </span>
        )
      )}
      <button
        onClick={() => handlePageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Next
      </button>
      {showFirstLast && (
        <button
          onClick={() => handlePageChange(totalPages)}
          disabled={currentPage === totalPages}
          className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Last
        </button>
      )}
    </nav>
  );
};
