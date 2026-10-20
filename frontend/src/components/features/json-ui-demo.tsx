/**
 * JSON UI Demo Component
 * Can be embedded anywhere to showcase the renderer
 */

'use client';

import React from 'react';
import { JSONUIRenderer } from '@/lib/ui-renderer';
import { UISchema } from '@/types/ui-schema';

const simpleExample: UISchema = {
  version: '1.0',
  metadata: {
    title: 'Simple Example',
    description: 'A quick demonstration of the JSON UI Renderer',
  },
  components: [
    {
      type: 'card',
      props: {
        title: 'Welcome to JSON UI Renderer',
        subtitle: 'Build UIs dynamically from JSON',
      },
      children: [
        {
          type: 'stack',
          props: {
            direction: 'vertical',
            gap: 4,
          },
          children: [
            {
              type: 'text',
              props: {
                content: 'This component is rendered from a JSON schema. You can define entire UIs using simple JSON objects.',
              },
            },
            {
              type: 'alert',
              props: {
                variant: 'info',
                message: 'The renderer supports 50+ component types including layouts, forms, tables, charts, and more.',
              },
            },
            {
              type: 'grid',
              props: {
                columns: 3,
                gap: 4,
              },
              children: [
                {
                  type: 'card',
                  props: {
                    variant: 'bordered',
                  },
                  children: [
                    {
                      type: 'badge',
                      props: {
                        label: 'Type Safe',
                        variant: 'success',
                      },
                    },
                    {
                      type: 'text',
                      props: {
                        content: 'Full TypeScript support with comprehensive type definitions.',
                        size: 'sm',
                      },
                    },
                  ],
                },
                {
                  type: 'card',
                  props: {
                    variant: 'bordered',
                  },
                  children: [
                    {
                      type: 'badge',
                      props: {
                        label: 'Extensible',
                        variant: 'primary',
                      },
                    },
                    {
                      type: 'text',
                      props: {
                        content: 'Easy to add custom components via the component registry.',
                        size: 'sm',
                      },
                    },
                  ],
                },
                {
                  type: 'card',
                  props: {
                    variant: 'bordered',
                  },
                  children: [
                    {
                      type: 'badge',
                      props: {
                        label: 'Scalable',
                        variant: 'warning',
                      },
                    },
                    {
                      type: 'text',
                      props: {
                        content: 'Designed for cloud-model-generated UIs and dynamic rendering.',
                        size: 'sm',
                      },
                    },
                  ],
                },
              ],
            },
            {
              type: 'row',
              props: {
                gap: 3,
                justify: 'center',
              },
              children: [
                {
                  type: 'button',
                  props: {
                    label: 'View Examples',
                    variant: 'primary',
                  },
                },
                {
                  type: 'button',
                  props: {
                    label: 'Read Docs',
                    variant: 'outline',
                  },
                },
              ],
            },
          ],
        },
      ],
    },
  ],
};

export const JSONUIDemo: React.FC = () => {
  return (
    <div className="w-full">
      <JSONUIRenderer schema={simpleExample} />
    </div>
  );
};
