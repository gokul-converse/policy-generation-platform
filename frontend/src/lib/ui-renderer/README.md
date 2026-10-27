# JSON UI Renderer

A type-safe, extensible JSON-driven UI rendering system for Next.js.

## Quick Start

```tsx
import { JSONUIRenderer } from '@/lib/ui-renderer';

const schema = {
  version: '1.0',
  components: [
    {
      type: 'heading',
      props: { content: 'Hello World', level: 1 }
    }
  ]
};

<JSONUIRenderer schema={schema} />
```

## Structure

```
ui-renderer/
├── components/          # Component implementations
│   ├── layout.tsx      # Container, Grid, Row, Column, Stack
│   ├── typography.tsx  # Heading, Text, Link, Paragraph
│   ├── ui-elements.tsx # Button, Badge, Alert, Card, etc.
│   ├── forms.tsx       # Form, Input, Textarea, Select, etc.
│   ├── interactive.tsx # Accordion, Tabs
│   ├── data-display.tsx # Table, Metrics, Progress, Chart
│   └── navigation.tsx  # Nav, Breadcrumb, Pagination
├── examples/           # JSON examples
│   ├── dashboard-example.json
│   ├── form-example.json
│   └── interactive-example.json
├── utils/              # Utilities
│   └── validation.ts   # Schema validation
├── registry.ts         # Component registry
├── renderer.tsx        # Main renderer
└── index.ts           # Public exports
```

## Features

- ✅ 50+ component types
- ✅ Type-safe TypeScript definitions
- ✅ Component registry system
- ✅ Responsive layouts
- ✅ Data binding support
- ✅ Validation utilities
- ✅ Error boundaries

## Documentation

See [JSON-UI-RENDERER.md](../../../JSON-UI-RENDERER.md) for complete documentation.

## Demo

Visit `/demo-renderer` to see interactive examples.

## Adding Custom Components

1. Create component in `components/`
2. Register with `componentRegistry.register()`
3. Add type to `ComponentType` in `ui-schema.ts`
4. Use in JSON with your custom type

Example:

```tsx
import { componentRegistry } from '@/lib/ui-renderer';

const MyComponent = ({ text }: { text: string }) => <div>{text}</div>;

componentRegistry.register('myComponent', MyComponent);
```

## Validation

```tsx
import { validateUISchema, getErrorSummary } from '@/lib/ui-renderer/utils';

const result = validateUISchema(schema);
if (!result.valid) {
  console.error(getErrorSummary(result));
}
```

## Component Types

Layout: `container`, `grid`, `row`, `column`, `stack`, `spacer`  
Typography: `heading`, `text`, `paragraph`, `link`  
UI: `button`, `badge`, `alert`, `card`, `divider`, `image`  
Forms: `form`, `input`, `textarea`, `select`, `checkbox`, `radio`, `switch`  
Interactive: `accordion`, `tabs`  
Data: `table`, `list`, `metrics`, `chart`, `progress`  
Navigation: `nav`, `breadcrumb`, `pagination`

## Support

See main project documentation or contact the development team.
