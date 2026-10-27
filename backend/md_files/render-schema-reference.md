# Render Schema Reference

## Introduction

This document provides a complete reference for all components, layouts, and properties supported by the JSON UI renderer. Each component is documented with its schema structure, required and optional properties, supported CSS properties, and JSON examples.

**Important**: All measurements in JSON must be strings with units: `"1rem"`, `"16px"`, `"100%"`, `"2em"`. Never use bare numbers for CSS properties.

---

## Table of Contents

1. [Component Overview](#component-overview)
2. [Layout Components](#layout-components)
3. [Typography Components](#typography-components)
4. [Form Components](#form-components)
5. [Interactive Components](#interactive-components)
6. [Display Components](#display-components)
7. [CSS Properties Reference](#css-properties-reference)
8. [Action System](#action-system)

---

## Component Overview

All components share a common base structure:

```json
{
  "id": "unique-identifier",
  "type": "ComponentName",
  "props": {
    // Component-specific properties
  },
  "styles": {
    // CSS properties as strings
  },
  "children": [
    // Nested components (if supported)
  ]
}
```

### Base Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | string | Yes | Unique identifier for the component |
| `type` | string | Yes | Component type name (exact match required) |
| `props` | object | No | Component-specific properties |
| `styles` | object | No | CSS properties (all values as strings) |
| `children` | array | No | Child components (for container types) |

---

## Layout Components

### Container

General-purpose container for grouping elements.

**Type**: `"Container"`

**Props**:
- None required
- All layout controlled via `styles`

**Supports Children**: Yes

**Example**:
```json
{
  "id": "main-container",
  "type": "Container",
  "styles": {
    "padding": "2rem",
    "maxWidth": "1200px",
    "margin": "0 auto"
  },
  "children": [
    {
      "id": "header",
      "type": "Heading",
      "props": { "level": 1, "text": "Welcome" }
    }
  ]
}
```

---

### Section

Semantic section container, renders as `<section>` element.

**Type**: `"Section"`

**Props**:
- None required
- All layout controlled via `styles`

**Supports Children**: Yes

**Example**:
```json
{
  "id": "hero-section",
  "type": "Section",
  "styles": {
    "backgroundColor": "#f0f0f0",
    "padding": "4rem 2rem",
    "textAlign": "center"
  },
  "children": [
    {
      "id": "hero-title",
      "type": "Heading",
      "props": { "level": 1, "text": "Hero Title" }
    }
  ]
}
```

---

### Flex

Flexbox layout container.

**Type**: `"Flex"`

**Props**:
- `direction` (optional): `"row"` | `"column"` | `"row-reverse"` | `"column-reverse"`
- `justify` (optional): `"flex-start"` | `"center"` | `"flex-end"` | `"space-between"` | `"space-around"` | `"space-evenly"`
- `align` (optional): `"flex-start"` | `"center"` | `"flex-end"` | `"stretch"` | `"baseline"`
- `wrap` (optional): `"nowrap"` | `"wrap"` | `"wrap-reverse"`
- `gap` (optional): string with unit (e.g., `"1rem"`, `"16px"`)

**Supports Children**: Yes

**Example**:
```json
{
  "id": "button-row",
  "type": "Flex",
  "props": {
    "direction": "row",
    "justify": "center",
    "align": "center",
    "gap": "1rem"
  },
  "styles": {
    "padding": "1rem"
  },
  "children": [
    {
      "id": "btn1",
      "type": "Button",
      "props": { "text": "Cancel", "variant": "outline" }
    },
    {
      "id": "btn2",
      "type": "Button",
      "props": { "text": "Submit", "variant": "primary" }
    }
  ]
}
```

---

### Grid

CSS Grid layout container.

**Type**: `"Grid"`

**Props**:
- `columns` (optional): number or string (e.g., `3`, `"repeat(3, 1fr)"`, `"200px 1fr 200px"`)
- `rows` (optional): number or string
- `gap` (optional): string with unit
- `columnGap` (optional): string with unit
- `rowGap` (optional): string with unit

**Supports Children**: Yes

**Example**:
```json
{
  "id": "card-grid",
  "type": "Grid",
  "props": {
    "columns": "repeat(3, 1fr)",
    "gap": "2rem"
  },
  "styles": {
    "padding": "2rem"
  },
  "children": [
    {
      "id": "card1",
      "type": "Card",
      "props": { "title": "Card 1" },
      "children": [
        { "id": "text1", "type": "Text", "props": { "text": "Content 1" } }
      ]
    },
    {
      "id": "card2",
      "type": "Card",
      "props": { "title": "Card 2" },
      "children": [
        { "id": "text2", "type": "Text", "props": { "text": "Content 2" } }
      ]
    }
  ]
}
```

---

### Stack

Vertical stacking layout with consistent spacing.

**Type**: `"Stack"`

**Props**:
- `spacing` (optional): string with unit (default: `"1rem"`)

**Supports Children**: Yes

**Example**:
```json
{
  "id": "form-stack",
  "type": "Stack",
  "props": {
    "spacing": "1.5rem"
  },
  "children": [
    {
      "id": "name-input",
      "type": "Input",
      "props": { "type": "text", "placeholder": "Name" }
    },
    {
      "id": "email-input",
      "type": "Input",
      "props": { "type": "email", "placeholder": "Email" }
    }
  ]
}
```

---

### Card

Card container with optional header and footer.

**Type**: `"Card"`

**Props**:
- `title` (optional): string - displays in card header
- `subtitle` (optional): string - displays below title
- `footer` (optional): string - displays in card footer

**Supports Children**: Yes (rendered in card body)

**Example**:
```json
{
  "id": "user-card",
  "type": "Card",
  "props": {
    "title": "User Profile",
    "subtitle": "Account Information",
    "footer": "Last updated: Jan 2025"
  },
  "styles": {
    "maxWidth": "400px",
    "margin": "1rem"
  },
  "children": [
    {
      "id": "user-name",
      "type": "Text",
      "props": { "text": "John Doe" }
    },
    {
      "id": "user-email",
      "type": "Text",
      "props": { "text": "john@example.com" }
    }
  ]
}
```

---

### Divider

Horizontal or vertical divider line.

**Type**: `"Divider"`

**Props**:
- `orientation` (optional): `"horizontal"` | `"vertical"` (default: `"horizontal"`)
- `thickness` (optional): string with unit (default: `"1px"`)
- `color` (optional): string (default: `"#e0e0e0"`)

**Supports Children**: No

**Example**:
```json
{
  "id": "section-divider",
  "type": "Divider",
  "props": {
    "orientation": "horizontal",
    "thickness": "2px",
    "color": "#cccccc"
  },
  "styles": {
    "margin": "2rem 0"
  }
}
```

---

### Spacer

Flexible spacing element.

**Type**: `"Spacer"`

**Props**:
- `size` (optional): string with unit (default: `"1rem"`)

**Supports Children**: No

**Example**:
```json
{
  "id": "spacer1",
  "type": "Spacer",
  "props": {
    "size": "3rem"
  }
}
```

---

## Typography Components

### Heading

Semantic heading element (h1-h6).

**Type**: `"Heading"`

**Props**:
- `text` (required): string - heading content
- `level` (required): number (1-6) - heading level
- `as` (optional): `"h1"` | `"h2"` | `"h3"` | `"h4"` | `"h5"` | `"h6"` - override semantic element

**Supports Children**: No

**Example**:
```json
{
  "id": "page-title",
  "type": "Heading",
  "props": {
    "text": "Policy Generation Platform",
    "level": 1
  },
  "styles": {
    "fontSize": "2.5rem",
    "fontWeight": "700",
    "color": "#1a1a1a",
    "marginBottom": "1rem"
  }
}
```

---

### Text

Paragraph or inline text element.

**Type**: `"Text"`

**Props**:
- `text` (required): string - text content
- `as` (optional): `"p"` | `"span"` | `"div"` - HTML element type (default: `"p"`)

**Supports Children**: No

**Example**:
```json
{
  "id": "description",
  "type": "Text",
  "props": {
    "text": "Enter your policy requirements below.",
    "as": "p"
  },
  "styles": {
    "fontSize": "1rem",
    "lineHeight": "1.6",
    "color": "#666666"
  }
}
```

---

### Label

Form label element.

**Type**: `"Label"`

**Props**:
- `text` (required): string - label text
- `htmlFor` (optional): string - associates with input id

**Supports Children**: No

**Example**:
```json
{
  "id": "name-label",
  "type": "Label",
  "props": {
    "text": "Full Name",
    "htmlFor": "name-input"
  },
  "styles": {
    "fontSize": "0.875rem",
    "fontWeight": "600",
    "marginBottom": "0.5rem",
    "display": "block"
  }
}
```

---

### Link

Hyperlink element.

**Type**: `"Link"`

**Props**:
- `text` (required): string - link text
- `href` (required): string - URL or path
- `target` (optional): `"_blank"` | `"_self"` | `"_parent"` | `"_top"`
- `rel` (optional): string (e.g., `"noopener noreferrer"`)

**Supports Children**: No

**Example**:
```json
{
  "id": "docs-link",
  "type": "Link",
  "props": {
    "text": "View Documentation",
    "href": "https://docs.example.com",
    "target": "_blank",
    "rel": "noopener noreferrer"
  },
  "styles": {
    "color": "#0066cc",
    "textDecoration": "underline",
    "fontSize": "1rem"
  }
}
```

---

## Form Components

### Input

Text input field.

**Type**: `"Input"`

**Props**:
- `type` (optional): `"text"` | `"email"` | `"password"` | `"number"` | `"tel"` | `"url"` | `"search"` (default: `"text"`)
- `placeholder` (optional): string
- `value` (optional): string - controlled value
- `defaultValue` (optional): string - uncontrolled default
- `name` (optional): string - form field name
- `required` (optional): boolean
- `disabled` (optional): boolean
- `readOnly` (optional): boolean
- `min` (optional): number (for type="number")
- `max` (optional): number (for type="number")
- `step` (optional): number (for type="number")
- `pattern` (optional): string - regex validation
- `maxLength` (optional): number

**Supports Children**: No

**Example**:
```json
{
  "id": "email-input",
  "type": "Input",
  "props": {
    "type": "email",
    "placeholder": "your.email@example.com",
    "name": "email",
    "required": true
  },
  "styles": {
    "width": "100%",
    "padding": "0.75rem",
    "fontSize": "1rem",
    "border": "1px solid #cccccc",
    "borderRadius": "4px"
  }
}
```

---

### Textarea

Multi-line text input.

**Type**: `"Textarea"`

**Props**:
- `placeholder` (optional): string
- `value` (optional): string - controlled value
- `defaultValue` (optional): string - uncontrolled default
- `name` (optional): string
- `required` (optional): boolean
- `disabled` (optional): boolean
- `readOnly` (optional): boolean
- `rows` (optional): number - visible rows
- `cols` (optional): number - visible columns
- `maxLength` (optional): number

**Supports Children**: No

**Example**:
```json
{
  "id": "policy-description",
  "type": "Textarea",
  "props": {
    "placeholder": "Describe your policy requirements...",
    "name": "description",
    "rows": 6,
    "required": true
  },
  "styles": {
    "width": "100%",
    "padding": "0.75rem",
    "fontSize": "1rem",
    "border": "1px solid #cccccc",
    "borderRadius": "4px",
    "fontFamily": "inherit",
    "resize": "vertical"
  }
}
```

---

### Select

Dropdown selection field.

**Type**: `"Select"`

**Props**:
- `options` (required): array of `{ value: string, label: string }`
- `value` (optional): string - controlled value
- `defaultValue` (optional): string - uncontrolled default
- `name` (optional): string
- `required` (optional): boolean
- `disabled` (optional): boolean
- `multiple` (optional): boolean - allow multiple selections

**Supports Children**: No

**Example**:
```json
{
  "id": "department-select",
  "type": "Select",
  "props": {
    "options": [
      { "value": "hr", "label": "Human Resources" },
      { "value": "it", "label": "Information Technology" },
      { "value": "finance", "label": "Finance" }
    ],
    "name": "department",
    "required": true,
    "defaultValue": "hr"
  },
  "styles": {
    "width": "100%",
    "padding": "0.75rem",
    "fontSize": "1rem",
    "border": "1px solid #cccccc",
    "borderRadius": "4px"
  }
}
```

---

### Checkbox

Checkbox input.

**Type**: `"Checkbox"`

**Props**:
- `label` (optional): string - checkbox label
- `checked` (optional): boolean - controlled checked state
- `defaultChecked` (optional): boolean - uncontrolled default
- `name` (optional): string
- `value` (optional): string
- `required` (optional): boolean
- `disabled` (optional): boolean

**Supports Children**: No

**Example**:
```json
{
  "id": "terms-checkbox",
  "type": "Checkbox",
  "props": {
    "label": "I agree to the terms and conditions",
    "name": "termsAccepted",
    "required": true
  },
  "styles": {
    "marginTop": "1rem"
  }
}
```

---

### Radio

Radio button input.

**Type**: `"Radio"`

**Props**:
- `label` (optional): string - radio label
- `name` (required): string - radio group name
- `value` (required): string - radio value
- `checked` (optional): boolean - controlled checked state
- `defaultChecked` (optional): boolean - uncontrolled default
- `required` (optional): boolean
- `disabled` (optional): boolean

**Supports Children**: No

**Example**:
```json
{
  "id": "option-a",
  "type": "Radio",
  "props": {
    "label": "Option A",
    "name": "choice",
    "value": "a"
  }
}
```

---

### RadioGroup

Container for radio button groups with automatic name handling.

**Type**: `"RadioGroup"`

**Props**:
- `name` (required): string - group name for all radios
- `options` (required): array of `{ value: string, label: string }`
- `value` (optional): string - controlled selected value
- `defaultValue` (optional): string - uncontrolled default

**Supports Children**: No (uses options prop)

**Example**:
```json
{
  "id": "policy-type-group",
  "type": "RadioGroup",
  "props": {
    "name": "policyType",
    "options": [
      { "value": "security", "label": "Security Policy" },
      { "value": "privacy", "label": "Privacy Policy" },
      { "value": "conduct", "label": "Code of Conduct" }
    ],
    "defaultValue": "security"
  },
  "styles": {
    "display": "flex",
    "flexDirection": "column",
    "gap": "0.75rem"
  }
}
```

---

### Form

Form container with submit handling.

**Type**: `"Form"`

**Props**:
- `onSubmit` (optional): action object - action to execute on submit
- `method` (optional): `"get"` | `"post"` (default: `"post"`)
- `action` (optional): string - form action URL

**Supports Children**: Yes

**Example**:
```json
{
  "id": "policy-form",
  "type": "Form",
  "props": {
    "onSubmit": {
      "type": "api",
      "config": {
        "url": "/api/policies",
        "method": "POST"
      }
    }
  },
  "children": [
    {
      "id": "title-input",
      "type": "Input",
      "props": { "name": "title", "placeholder": "Policy Title" }
    },
    {
      "id": "submit-btn",
      "type": "Button",
      "props": { "text": "Submit", "type": "submit" }
    }
  ]
}
```

---

## Interactive Components

### Button

Button element with action support.

**Type**: `"Button"`

**Props**:
- `text` (required): string - button text
- `variant` (optional): `"primary"` | `"secondary"` | `"outline"` | `"ghost"` | `"danger"`
- `size` (optional): `"sm"` | `"md"` | `"lg"`
- `type` (optional): `"button"` | `"submit"` | `"reset"` (default: `"button"`)
- `disabled` (optional): boolean
- `onClick` (optional): action object - action to execute on click

**Supports Children**: No

**Example**:
```json
{
  "id": "generate-btn",
  "type": "Button",
  "props": {
    "text": "Generate Policy",
    "variant": "primary",
    "size": "lg",
    "onClick": {
      "type": "api",
      "config": {
        "url": "/api/generate",
        "method": "POST",
        "body": {
          "description": "{{formData.description}}"
        }
      }
    }
  },
  "styles": {
    "marginTop": "1.5rem",
    "width": "100%"
  }
}
```

---

### Badge

Small status or label badge.

**Type**: `"Badge"`

**Props**:
- `text` (required): string - badge text
- `variant` (optional): `"default"` | `"success"` | `"warning"` | `"error"` | `"info"`

**Supports Children**: No

**Example**:
```json
{
  "id": "status-badge",
  "type": "Badge",
  "props": {
    "text": "Active",
    "variant": "success"
  },
  "styles": {
    "marginLeft": "0.5rem"
  }
}
```

---

### Icon

Icon display component (requires icon library integration).

**Type**: `"Icon"`

**Props**:
- `name` (required): string - icon name from icon library
- `size` (optional): string with unit (default: `"1rem"`)
- `color` (optional): string (default: inherits from parent)

**Supports Children**: No

**Example**:
```json
{
  "id": "check-icon",
  "type": "Icon",
  "props": {
    "name": "check-circle",
    "size": "1.5rem",
    "color": "#22c55e"
  }
}
```

---

### Image

Image element.

**Type**: `"Image"`

**Props**:
- `src` (required): string - image URL or path
- `alt` (required): string - alternative text
- `width` (optional): string with unit
- `height` (optional): string with unit
- `objectFit` (optional): `"contain"` | `"cover"` | `"fill"` | `"none"` | `"scale-down"`

**Supports Children**: No

**Example**:
```json
{
  "id": "logo",
  "type": "Image",
  "props": {
    "src": "/images/logo.png",
    "alt": "Company Logo",
    "width": "200px",
    "height": "60px",
    "objectFit": "contain"
  }
}
```

---

### Spinner

Loading spinner indicator.

**Type**: `"Spinner"`

**Props**:
- `size` (optional): string with unit (default: `"2rem"`)
- `color` (optional): string (default: `"#0066cc"`)

**Supports Children**: No

**Example**:
```json
{
  "id": "loading-spinner",
  "type": "Spinner",
  "props": {
    "size": "3rem",
    "color": "#0066cc"
  },
  "styles": {
    "margin": "2rem auto",
    "display": "block"
  }
}
```

---

### ProgressBar

Progress indicator bar.

**Type**: `"ProgressBar"`

**Props**:
- `value` (required): number (0-100) - progress percentage
- `max` (optional): number (default: 100)
- `showLabel` (optional): boolean - show percentage text
- `color` (optional): string - progress bar color

**Supports Children**: No

**Example**:
```json
{
  "id": "upload-progress",
  "type": "ProgressBar",
  "props": {
    "value": 65,
    "showLabel": true,
    "color": "#0066cc"
  },
  "styles": {
    "width": "100%",
    "height": "1rem"
  }
}
```

---

### Tooltip

Tooltip wrapper (requires hover support).

**Type**: `"Tooltip"`

**Props**:
- `content` (required): string - tooltip text
- `position` (optional): `"top"` | `"right"` | `"bottom"` | `"left"` (default: `"top"`)

**Supports Children**: Yes (single child that triggers tooltip)

**Example**:
```json
{
  "id": "help-tooltip",
  "type": "Tooltip",
  "props": {
    "content": "Click to view more information",
    "position": "top"
  },
  "children": [
    {
      "id": "help-icon",
      "type": "Icon",
      "props": { "name": "help-circle" }
    }
  ]
}
```

---

### Tabs

Tabbed content interface.

**Type**: `"Tabs"`

**Props**:
- `tabs` (required): array of `{ id: string, label: string, content: Component }`
- `defaultTab` (optional): string - id of default active tab

**Supports Children**: No (uses tabs prop)

**Example**:
```json
{
  "id": "policy-tabs",
  "type": "Tabs",
  "props": {
    "tabs": [
      {
        "id": "overview",
        "label": "Overview",
        "content": {
          "id": "overview-content",
          "type": "Text",
          "props": { "text": "Policy overview content" }
        }
      },
      {
        "id": "details",
        "label": "Details",
        "content": {
          "id": "details-content",
          "type": "Text",
          "props": { "text": "Policy details content" }
        }
      }
    ],
    "defaultTab": "overview"
  }
}
```

---

### Accordion

Expandable/collapsible sections.

**Type**: `"Accordion"`

**Props**:
- `items` (required): array of `{ id: string, title: string, content: Component }`
- `defaultExpanded` (optional): string[] - ids of initially expanded items
- `allowMultiple` (optional): boolean - allow multiple items open (default: true)

**Supports Children**: No (uses items prop)

**Example**:
```json
{
  "id": "faq-accordion",
  "type": "Accordion",
  "props": {
    "items": [
      {
        "id": "q1",
        "title": "What is a policy?",
        "content": {
          "id": "a1",
          "type": "Text",
          "props": { "text": "A policy is a formal statement..." }
        }
      },
      {
        "id": "q2",
        "title": "How do I generate a policy?",
        "content": {
          "id": "a2",
          "type": "Text",
          "props": { "text": "Click the Generate button..." }
        }
      }
    ],
    "defaultExpanded": ["q1"],
    "allowMultiple": true
  }
}
```

---

### Modal

Modal dialog overlay.

**Type**: `"Modal"`

**Props**:
- `title` (optional): string - modal header title
- `isOpen` (required): boolean - controlled open state
- `onClose` (optional): action object - action when modal closes
- `size` (optional): `"sm"` | `"md"` | `"lg"` | `"xl"` | `"full"`
- `closeOnOverlayClick` (optional): boolean (default: true)

**Supports Children**: Yes (modal body content)

**Example**:
```json
{
  "id": "confirm-modal",
  "type": "Modal",
  "props": {
    "title": "Confirm Action",
    "isOpen": true,
    "size": "md"
  },
  "children": [
    {
      "id": "modal-text",
      "type": "Text",
      "props": { "text": "Are you sure you want to proceed?" }
    },
    {
      "id": "modal-buttons",
      "type": "Flex",
      "props": { "justify": "flex-end", "gap": "1rem" },
      "children": [
        {
          "id": "cancel-btn",
          "type": "Button",
          "props": { "text": "Cancel", "variant": "outline" }
        },
        {
          "id": "confirm-btn",
          "type": "Button",
          "props": { "text": "Confirm", "variant": "primary" }
        }
      ]
    }
  ]
}
```

---

### Alert

Alert or notification message.

**Type**: `"Alert"`

**Props**:
- `message` (required): string - alert message
- `variant` (optional): `"info"` | `"success"` | `"warning"` | `"error"` (default: `"info"`)
- `title` (optional): string - alert title
- `dismissible` (optional): boolean - show close button

**Supports Children**: No

**Example**:
```json
{
  "id": "success-alert",
  "type": "Alert",
  "props": {
    "title": "Success",
    "message": "Policy generated successfully!",
    "variant": "success",
    "dismissible": true
  },
  "styles": {
    "marginBottom": "1rem"
  }
}
```

---

### Table

Data table component.

**Type**: `"Table"`

**Props**:
- `columns` (required): array of `{ key: string, label: string, width?: string }`
- `data` (required): array of objects (keys match column keys)
- `striped` (optional): boolean - alternate row colors
- `hoverable` (optional): boolean - highlight on hover

**Supports Children**: No

**Example**:
```json
{
  "id": "policies-table",
  "type": "Table",
  "props": {
    "columns": [
      { "key": "id", "label": "ID", "width": "80px" },
      { "key": "title", "label": "Title" },
      { "key": "status", "label": "Status", "width": "120px" }
    ],
    "data": [
      { "id": "1", "title": "Security Policy", "status": "Active" },
      { "id": "2", "title": "Privacy Policy", "status": "Draft" }
    ],
    "striped": true,
    "hoverable": true
  },
  "styles": {
    "width": "100%"
  }
}
```

---

### List

Ordered or unordered list.

**Type**: `"List"`

**Props**:
- `items` (required): array of strings or component objects
- `ordered` (optional): boolean - use `<ol>` instead of `<ul>`
- `marker` (optional): string - custom list marker (CSS list-style-type)

**Supports Children**: No (uses items prop)

**Example**:
```json
{
  "id": "requirements-list",
  "type": "List",
  "props": {
    "items": [
      "Must include security measures",
      "Should specify data retention",
      "Must comply with GDPR"
    ],
    "ordered": true
  },
  "styles": {
    "marginLeft": "1.5rem",
    "lineHeight": "1.8"
  }
}
```

---

## Display Components

### Code

Code display block with syntax highlighting support.

**Type**: `"Code"`

**Props**:
- `code` (required): string - code content
- `language` (optional): string - language for syntax highlighting (e.g., `"javascript"`, `"python"`)
- `inline` (optional): boolean - inline code vs block (default: false)
- `showLineNumbers` (optional): boolean - show line numbers

**Supports Children**: No

**Example**:
```json
{
  "id": "code-example",
  "type": "Code",
  "props": {
    "code": "const policy = { title: 'Security Policy', version: 1 };",
    "language": "javascript",
    "showLineNumbers": true
  },
  "styles": {
    "marginTop": "1rem",
    "borderRadius": "4px"
  }
}
```

---

### Video

Video player component.

**Type**: `"Video"`

**Props**:
- `src` (required): string - video URL
- `poster` (optional): string - thumbnail image URL
- `controls` (optional): boolean (default: true)
- `autoplay` (optional): boolean
- `loop` (optional): boolean
- `muted` (optional): boolean
- `width` (optional): string with unit
- `height` (optional): string with unit

**Supports Children**: No

**Example**:
```json
{
  "id": "tutorial-video",
  "type": "Video",
  "props": {
    "src": "/videos/tutorial.mp4",
    "poster": "/images/video-thumbnail.jpg",
    "controls": true,
    "width": "100%"
  }
}
```

---

### Iframe

Embedded iframe content.

**Type**: `"Iframe"`

**Props**:
- `src` (required): string - iframe URL
- `title` (optional): string - accessibility title
- `width` (optional): string with unit
- `height` (optional): string with unit
- `allow` (optional): string - permissions policy
- `sandbox` (optional): string - sandbox restrictions

**Supports Children**: No

**Example**:
```json
{
  "id": "embedded-doc",
  "type": "Iframe",
  "props": {
    "src": "https://docs.example.com/embed",
    "title": "Documentation",
    "width": "100%",
    "height": "600px"
  },
  "styles": {
    "border": "1px solid #e0e0e0",
    "borderRadius": "4px"
  }
}
```

---

## CSS Properties Reference

All CSS properties must be provided as **strings with units**. Never use bare numbers.

### Spacing Properties

```json
{
  "margin": "1rem",
  "marginTop": "0.5rem",
  "marginRight": "1rem",
  "marginBottom": "1.5rem",
  "marginLeft": "1rem",
  "padding": "2rem",
  "paddingTop": "1rem",
  "paddingRight": "1.5rem",
  "paddingBottom": "1rem",
  "paddingLeft": "1.5rem",
  "gap": "1rem"
}
```

**Valid units**: `rem`, `em`, `px`, `%`, `vh`, `vw`

---

### Sizing Properties

```json
{
  "width": "100%",
  "minWidth": "300px",
  "maxWidth": "1200px",
  "height": "400px",
  "minHeight": "200px",
  "maxHeight": "80vh"
}
```

**Valid values**:
- Measurements: `"100px"`, `"50%"`, `"100vh"`, `"20rem"`
- Keywords: `"auto"`, `"fit-content"`, `"min-content"`, `"max-content"`

---

### Typography Properties

```json
{
  "fontSize": "1rem",
  "fontWeight": "600",
  "fontFamily": "'Inter', sans-serif",
  "lineHeight": "1.6",
  "letterSpacing": "0.05em",
  "textAlign": "center",
  "textDecoration": "underline",
  "textTransform": "uppercase",
  "color": "#1a1a1a"
}
```

**fontWeight values**: `"100"`, `"200"`, `"300"`, `"400"`, `"500"`, `"600"`, `"700"`, `"800"`, `"900"`, `"normal"`, `"bold"`

**textAlign values**: `"left"`, `"center"`, `"right"`, `"justify"`

---

### Color Properties

```json
{
  "color": "#1a1a1a",
  "backgroundColor": "#f0f0f0",
  "borderColor": "#cccccc",
  "opacity": "0.8"
}
```

**Valid formats**:
- Hex: `"#ff0000"`, `"#f00"`
- RGB: `"rgb(255, 0, 0)"`
- RGBA: `"rgba(255, 0, 0, 0.5)"`
- Named: `"red"`, `"blue"`, `"transparent"`

---

### Border Properties

```json
{
  "border": "1px solid #cccccc",
  "borderTop": "2px solid #000000",
  "borderRight": "1px dashed #999999",
  "borderBottom": "3px double #333333",
  "borderLeft": "1px solid #cccccc",
  "borderWidth": "2px",
  "borderStyle": "solid",
  "borderColor": "#e0e0e0",
  "borderRadius": "8px"
}
```

**borderStyle values**: `"solid"`, `"dashed"`, `"dotted"`, `"double"`, `"none"`

---

### Layout Properties

```json
{
  "display": "flex",
  "flexDirection": "row",
  "justifyContent": "center",
  "alignItems": "center",
  "flexWrap": "wrap",
  "flexGrow": "1",
  "flexShrink": "0",
  "flexBasis": "200px",
  "gridTemplateColumns": "repeat(3, 1fr)",
  "gridTemplateRows": "auto",
  "gridGap": "1rem",
  "position": "relative",
  "top": "0",
  "right": "0",
  "bottom": "0",
  "left": "0",
  "zIndex": "10"
}
```

**display values**: `"block"`, `"inline"`, `"inline-block"`, `"flex"`, `"grid"`, `"none"`

**position values**: `"static"`, `"relative"`, `"absolute"`, `"fixed"`, `"sticky"`

---

### Effect Properties

```json
{
  "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
  "textShadow": "1px 1px 2px rgba(0,0,0,0.2)",
  "filter": "blur(4px)",
  "transform": "rotate(45deg)",
  "transition": "all 0.3s ease",
  "cursor": "pointer",
  "overflow": "hidden",
  "overflowX": "auto",
  "overflowY": "scroll"
}
```

**cursor values**: `"auto"`, `"pointer"`, `"default"`, `"text"`, `"move"`, `"not-allowed"`

**overflow values**: `"visible"`, `"hidden"`, `"scroll"`, `"auto"`

---

## Action System

Actions define interactive behavior for components. All actions follow this base structure:

```json
{
  "type": "ActionType",
  "config": {
    // Action-specific configuration
  }
}
```

### Action Types

#### Navigate Action

Navigate to a different page or route.

**Type**: `"navigate"`

**Config**:
- `path` (required): string - target path
- `replace` (optional): boolean - replace history instead of push

```json
{
  "type": "navigate",
  "config": {
    "path": "/policies/new",
    "replace": false
  }
}
```

---

#### API Action

Make an HTTP API request.

**Type**: `"api"`

**Config**:
- `url` (required): string - API endpoint
- `method` (required): `"GET"` | `"POST"` | `"PUT"` | `"PATCH"` | `"DELETE"`
- `headers` (optional): object - HTTP headers
- `body` (optional): object - request body (for POST/PUT/PATCH)
- `onSuccess` (optional): action object - action to execute on success
- `onError` (optional): action object - action to execute on error

```json
{
  "type": "api",
  "config": {
    "url": "/api/policies",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "title": "{{formData.title}}",
      "description": "{{formData.description}}"
    },
    "onSuccess": {
      "type": "navigate",
      "config": { "path": "/policies" }
    }
  }
}
```

---

#### SetState Action

Update application state.

**Type**: `"setState"`

**Config**:
- `key` (required): string - state key
- `value` (required): any - new value

```json
{
  "type": "setState",
  "config": {
    "key": "isLoading",
    "value": true
  }
}
```

---

#### Submit Action

Submit a form (use with Form component).

**Type**: `"submit"`

**Config**:
- `formId` (required): string - target form id

```json
{
  "type": "submit",
  "config": {
    "formId": "policy-form"
  }
}
```

---

#### Custom Action

Execute custom JavaScript code (if enabled).

**Type**: `"custom"`

**Config**:
- `handler` (required): string - function name or code

```json
{
  "type": "custom",
  "config": {
    "handler": "handleCustomAction"
  }
}
```

---

#### Log Action

Log data to console (debugging).

**Type**: `"log"`

**Config**:
- `message` (required): string - log message
- `data` (optional): any - additional data

```json
{
  "type": "log",
  "config": {
    "message": "Button clicked",
    "data": { "timestamp": "{{timestamp}}" }
  }
}
```

---

### Action Chaining

Actions can be chained using `onSuccess` and `onError`:

```json
{
  "type": "api",
  "config": {
    "url": "/api/validate",
    "method": "POST",
    "body": { "data": "{{formData}}" },
    "onSuccess": {
      "type": "api",
      "config": {
        "url": "/api/submit",
        "method": "POST",
        "body": { "validated": true },
        "onSuccess": {
          "type": "navigate",
          "config": { "path": "/success" }
        }
      }
    },
    "onError": {
      "type": "setState",
      "config": {
        "key": "error",
        "value": "Validation failed"
      }
    }
  }
}
```

---

### Variable Interpolation

Actions support variable interpolation using `{{variableName}}` syntax:

**Available variables**:
- `{{formData.fieldName}}` - form field values
- `{{state.key}}` - application state values
- `{{timestamp}}` - current timestamp
- `{{userId}}` - current user ID (if authenticated)

```json
{
  "type": "api",
  "config": {
    "url": "/api/users/{{userId}}/policies",
    "method": "POST",
    "body": {
      "title": "{{formData.title}}",
      "createdAt": "{{timestamp}}"
    }
  }
}
```

---

## Complete Example

Full policy generation form with all features:

```json
{
  "id": "root",
  "type": "Container",
  "styles": {
    "maxWidth": "800px",
    "margin": "0 auto",
    "padding": "2rem"
  },
  "children": [
    {
      "id": "header",
      "type": "Heading",
      "props": {
        "text": "Policy Generation",
        "level": 1
      },
      "styles": {
        "marginBottom": "0.5rem"
      }
    },
    {
      "id": "subtitle",
      "type": "Text",
      "props": {
        "text": "Create a new policy by providing the details below."
      },
      "styles": {
        "color": "#666666",
        "marginBottom": "2rem"
      }
    },
    {
      "id": "policy-form",
      "type": "Form",
      "props": {
        "onSubmit": {
          "type": "api",
          "config": {
            "url": "/api/policies/generate",
            "method": "POST",
            "onSuccess": {
              "type": "navigate",
              "config": { "path": "/policies/{{response.id}}" }
            }
          }
        }
      },
      "children": [
        {
          "id": "form-stack",
          "type": "Stack",
          "props": { "spacing": "1.5rem" },
          "children": [
            {
              "id": "title-field",
              "type": "Container",
              "children": [
                {
                  "id": "title-label",
                  "type": "Label",
                  "props": {
                    "text": "Policy Title",
                    "htmlFor": "title-input"
                  }
                },
                {
                  "id": "title-input",
                  "type": "Input",
                  "props": {
                    "type": "text",
                    "name": "title",
                    "placeholder": "e.g., Security Policy",
                    "required": true
                  },
                  "styles": {
                    "width": "100%",
                    "marginTop": "0.5rem"
                  }
                }
              ]
            },
            {
              "id": "type-field",
              "type": "Container",
              "children": [
                {
                  "id": "type-label",
                  "type": "Label",
                  "props": { "text": "Policy Type" }
                },
                {
                  "id": "type-select",
                  "type": "Select",
                  "props": {
                    "name": "type",
                    "options": [
                      { "value": "security", "label": "Security" },
                      { "value": "privacy", "label": "Privacy" },
                      { "value": "conduct", "label": "Code of Conduct" }
                    ],
                    "required": true
                  },
                  "styles": {
                    "width": "100%",
                    "marginTop": "0.5rem"
                  }
                }
              ]
            },
            {
              "id": "description-field",
              "type": "Container",
              "children": [
                {
                  "id": "description-label",
                  "type": "Label",
                  "props": {
                    "text": "Description",
                    "htmlFor": "description-textarea"
                  }
                },
                {
                  "id": "description-textarea",
                  "type": "Textarea",
                  "props": {
                    "name": "description",
                    "placeholder": "Describe your policy requirements...",
                    "rows": 6,
                    "required": true
                  },
                  "styles": {
                    "width": "100%",
                    "marginTop": "0.5rem"
                  }
                }
              ]
            },
            {
              "id": "button-row",
              "type": "Flex",
              "props": {
                "justify": "flex-end",
                "gap": "1rem"
              },
              "children": [
                {
                  "id": "cancel-btn",
                  "type": "Button",
                  "props": {
                    "text": "Cancel",
                    "variant": "outline",
                    "onClick": {
                      "type": "navigate",
                      "config": { "path": "/policies" }
                    }
                  }
                },
                {
                  "id": "submit-btn",
                  "type": "Button",
                  "props": {
                    "text": "Generate Policy",
                    "variant": "primary",
                    "type": "submit"
                  }
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Validation Rules

1. **Component Types**: Must exactly match documented types (case-sensitive)
2. **Required Props**: All props marked as required must be provided
3. **CSS Units**: All measurements must include units as strings
4. **IDs**: Must be unique within the entire JSON document
5. **Children**: Only provided for components that support children
6. **Action Types**: Must match documented action types exactly
7. **Enum Values**: Must match documented options exactly (case-sensitive)

---

## Error Handling

Common validation errors and fixes:

| Error | Fix |
|-------|-----|
| `Invalid component type` | Check type spelling and case |
| `Missing required prop` | Add all required props for component |
| `Invalid CSS value` | Add unit to measurement (e.g., `"1rem"` not `1`) |
| `Duplicate ID` | Ensure all component IDs are unique |
| `Children not supported` | Remove children array from component |
| `Invalid action type` | Check action type spelling and case |

---

## Best Practices

1. **Use rem units** for most spacing and typography to ensure consistent scaling
2. **Provide unique IDs** for all components to enable proper state management
3. **Use semantic HTML** by choosing appropriate component types (Heading vs Text)
4. **Group related inputs** in Forms or Stacks for better organization
5. **Add labels to inputs** for accessibility
6. **Use flexbox/grid** for complex layouts instead of absolute positioning
7. **Chain actions** for complex interactions (validate → submit → navigate)
8. **Provide alt text** for images for accessibility
9. **Use loading states** (Spinner) during async operations
10. **Handle errors gracefully** with Alert components and onError actions

---

## Version Information

- **Schema Version**: 1.0
- **Last Updated**: 2025-01-20
- **Renderer Version**: Compatible with Next.js 14+

For questions or issues with the schema, refer to the cloud-model-json-guide.md for additional context.



## UI Generation Quality Guidelines

### 1. Build the UI Around the Policy

- Identify the policy title, purpose, main sections, rules, responsibilities,
  procedures, exceptions, and other important details present in the input.
- Use only information explicitly provided by the policy.
- Preserve all material rules and conditions.
- Do not copy facts from the examples in this guide.
- Do not create statistics, policy metrics, or numerical summaries unless
  supported by the input.

### 2. Use Components Meaningfully

- Use `heading` for the page title and section headings.
- Use `paragraph` or `text` for explanations and descriptions.
- Use `list` for policy steps, responsibilities, and bullet points when
  supported by the renderer.
- Use `card` to group related information where it improves readability.
- Use `alert` only for meaningful warnings, notices, or important guidance.
- Use `accordion` for long sections when its supported item structure
  is known.
- Use `tabs` only for clearly separate content groups when its supported
  item structure is known.
- Use `divider`, `row`, `column`, `stack`, `grid`, and `container` to
  organize content when supported.
- Avoid adding forms, charts, metrics, or interactive controls unless
  the policy UI genuinely needs them.

### 3. Visual Design

- Create a clear visual hierarchy with a prominent title and distinct
  section headings.
- Use consistent spacing, typography, borders, and colors.
- Keep paragraphs readable and avoid overly wide text areas.
- Use responsive layouts and avoid fixed dimensions that unnecessarily
  constrain smaller screens.
- Use only CSS properties and component properties defined by this guide
  and supported by the frontend renderer.
- In `css`, represent CSS values with appropriate valid types. Use strings
  for values with units, such as `"1rem"`, `"16px"`, and `"100%"`.
- Do not confuse component-specific `props` with the `css` object.

### 4. Actions and Functional Behavior

- Do not generate actions simply to make the interface look interactive.
- Generate an action only when its purpose is clear and its type is
  supported by the actual frontend renderer.
- Every referenced action ID must exist in the root `actions` array.
- Never invent API endpoints, authentication details, backend operations,
  or custom handler implementations.
- If the frontend behavior is unknown, prefer a static presentation.

### 5. Missing Information

- Never fill gaps in the source policy using assumptions or example values.
- Include a missing-information notice only when it helps the reader
  understand an important unresolved detail.
- Do not present an unspecified rule as an established policy.

### 6. Final Output Check

Before returning the output, verify that:
1. The root contains `"version": "1.0"` and `"components"`.
2. Every component type is supported.
3. Required component properties are present.
4. Child components follow the documented nesting structure.
5. CSS values follow the documented rules.
6. All action references point to declared actions.
7. The UI preserves the source policy without invented facts.
8. The output is valid JSON without Markdown or commentary.
