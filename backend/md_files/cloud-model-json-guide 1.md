# Cloud Model JSON Schema Guide

## Overview
This guide provides the complete JSON schema structure for cloud models to generate valid React-compatible UI definitions. The JSON schema is converted to fully functional React components by the frontend renderer.

---

## Root Schema Structure

### Required Keys

```typescript
{
  "version": "1.0",        // ✅ Required - Must be exactly "1.0"
  "components": []         // ✅ Required - Array of component objects
}
```

### Optional Keys

```typescript
{
  "version": "1.0",
  "metadata": {            // ❓ Optional - Schema metadata
    "title": string,
    "description": string,
    "author": string,
    "createdAt": string
  },
  "actions": [],           // ❓ Optional - Action definitions array
  "dataSources": [],       // ❓ Optional - Data source definitions
  "components": []
}
```

### Complete Root Schema

```json
{
  "version": "1.0",
  "metadata": {
    "title": "Dashboard UI",
    "description": "Main dashboard interface",
    "author": "Cloud Model v2",
    "createdAt": "2024-01-20T10:00:00Z"
  },
  "actions": [
    {
      "id": "saveData",
      "type": "api",
      "config": {
        "endpoint": "/api/save",
        "method": "POST"
      }
    }
  ],
  "components": [
    {
      "type": "container",
      "props": {
        "maxWidth": "lg",
        "centered": true
      },
      "children": []
    }
  ]
}
```

---

## Component Schema Structure

### Base Component Structure

Every component follows this structure:

```typescript
{
  "type": string,                    // ✅ Required - Component type from supported list
  "props": object,                   // ❓ Optional - Component-specific properties
  "css": object,                     // ❓ Optional - CSS styling properties
  "children": array,                 // ❓ Optional - Nested child components
  "key": string                      // ❓ Optional - Unique key for lists
}
```

### Example Component

```json
{
  "type": "button",
  "props": {
    "label": "Save",
    "variant": "primary",
    "onClick": "saveData"
  },
  "css": {
    "paddingX": "2rem",
    "paddingY": "0.75rem",
    "fontSize": "1rem",
    "backgroundColor": "#3b82f6",
    "color": "#ffffff",
    "borderRadius": "0.5rem"
  }
}
```

---

## Supported Component Types

### Complete List (35 types)

```json
[
  "container", "grid", "row", "column", "stack", "spacer",
  "heading", "text", "paragraph", "link",
  "button", "badge", "alert", "card", "divider", "image",
  "form", "input", "textarea", "select", "checkbox", "radio", "switch",
  "accordion", "tabs", "modal", "dropdown",
  "table", "list", "metrics", "progress", "chart",
  "nav", "breadcrumb", "pagination"
]
```

### Required Props by Component Type

Some components require specific props:

```json
{
  "heading": ["content"],
  "text": ["content"],
  "paragraph": ["content"],
  "link": ["href", "content"],
  "button": ["label"],
  "badge": ["label"],
  "alert": ["message"],
  "image": ["src", "alt"],
  "input": ["name"],
  "textarea": ["name"],
  "select": ["name", "options"],
  "checkbox": ["name", "label"],
  "radio": ["name", "label", "value"],
  "table": ["columns", "data"],
  "accordion": ["items"],
  "tabs": ["items"]
}
```

---

## CSS Property Structure

### CSS Object Format

The `css` property accepts a flat object of CSS properties:

```json
{
  "css": {
    "display": "flex",
    "flexDirection": "column",
    "gap": "1.5rem",
    "padding": "2rem",
    "backgroundColor": "#ffffff",
    "borderRadius": "0.5rem"
  }
}
```

### CSS Unit Handling

**All CSS unit values must be strings:**

```json
{
  "css": {
    "padding": "2rem",           // ✅ Correct - rem units as string
    "margin": "16px",            // ✅ Correct - px units as string
    "width": "100%",             // ✅ Correct - percentage as string
    "height": "50vh",            // ✅ Correct - viewport units as string
    "fontSize": "1.5rem",        // ✅ Correct - rem units as string
    "lineHeight": "1.6",         // ✅ Correct - unitless as string
    "gap": "1rem",               // ✅ Correct - gap with rem
    "marginX": "auto",           // ✅ Correct - auto keyword
    "paddingY": "1.5rem"         // ✅ Correct - shortcut with rem
  }
}
```

**Common mistakes to avoid:**

```json
{
  "css": {
    "padding": 2,                // ❌ Wrong - numbers without units
    "margin": "2",               // ❌ Wrong - string number without units
    "fontSize": 16,              // ❌ Wrong - number instead of string
    "gap": 1.5                   // ❌ Wrong - number instead of string
  }
}
```

### Supported CSS Properties

#### Layout
```json
{
  "display": "flex | block | inline | inline-block | grid | none",
  "position": "static | relative | absolute | fixed | sticky",
  "top": "0 | 1rem | 10px",
  "right": "0 | 1rem | 10px",
  "bottom": "0 | 1rem | 10px",
  "left": "0 | 1rem | 10px",
  "zIndex": 0 | 10 | 20 | 30 | 40 | 50
}
```

#### Flexbox
```json
{
  "flexDirection": "row | row-reverse | column | column-reverse",
  "flexWrap": "nowrap | wrap | wrap-reverse",
  "justifyContent": "flex-start | flex-end | center | space-between | space-around | space-evenly",
  "alignItems": "flex-start | flex-end | center | baseline | stretch",
  "alignContent": "flex-start | flex-end | center | space-between | space-around | stretch",
  "flex": "1 | 0 0 auto | 1 1 0%",
  "flexGrow": 0 | 1 | 2,
  "flexShrink": 0 | 1,
  "flexBasis": "auto | 200px | 50%",
  "alignSelf": "auto | flex-start | flex-end | center | stretch",
  "order": -1 | 0 | 1,
  "gap": "0.5rem | 1rem | 1.5rem | 2rem"
}
```

#### Grid
```json
{
  "gridTemplateColumns": "repeat(3, 1fr) | 200px 1fr auto",
  "gridTemplateRows": "auto | 100px 200px",
  "gridColumn": "1 / 3 | span 2",
  "gridRow": "1 / 2 | span 3",
  "gridAutoFlow": "row | column | dense",
  "gridAutoColumns": "auto | 100px",
  "gridAutoRows": "auto | 100px",
  "gap": "1rem | 1.5rem | 2rem",
  "columnGap": "1rem",
  "rowGap": "1rem"
}
```

#### Spacing
```json
{
  "margin": "1rem | 2rem | 0",
  "marginTop": "1rem",
  "marginRight": "1rem",
  "marginBottom": "1rem",
  "marginLeft": "1rem",
  "marginX": "auto | 1rem | 2rem",
  "marginY": "1rem | 2rem",
  "padding": "1rem | 2rem | 0",
  "paddingTop": "1rem",
  "paddingRight": "1rem",
  "paddingBottom": "1rem",
  "paddingLeft": "1rem",
  "paddingX": "1rem | 2rem | 3rem",
  "paddingY": "1rem | 2rem"
}
```

**Note:** `marginX`, `marginY`, `paddingX`, `paddingY` are shortcuts that expand to individual properties.

#### Sizing
```json
{
  "width": "100% | 300px | 50vw | auto",
  "minWidth": "200px | 50%",
  "maxWidth": "800px | 100%",
  "height": "100% | 200px | 50vh | auto",
  "minHeight": "100px | 50vh",
  "maxHeight": "500px | 100vh"
}
```

#### Typography
```json
{
  "fontSize": "0.875rem | 1rem | 1.25rem | 1.5rem | 2rem",
  "fontWeight": "400 | 500 | 600 | 700 | 800 | normal | bold",
  "fontFamily": "Inter, sans-serif | Georgia, serif",
  "lineHeight": "1 | 1.5 | 1.6 | 24px",
  "letterSpacing": "0.05em | 1px | -0.5px",
  "textAlign": "left | center | right | justify",
  "textTransform": "none | uppercase | lowercase | capitalize",
  "textDecoration": "none | underline | line-through",
  "whiteSpace": "normal | nowrap | pre | pre-wrap",
  "wordBreak": "normal | break-all | break-word"
}
```

#### Colors
```json
{
  "color": "#1a202c | rgb(26, 32, 44) | rgba(0,0,0,0.8)",
  "backgroundColor": "#ffffff | #f9fafb | rgb(255,255,255)",
  "borderColor": "#e5e7eb | #3b82f6",
  "opacity": 0 | 0.5 | 0.8 | 1
}
```

#### Borders
```json
{
  "border": "1px solid #e5e7eb | 2px dashed #3b82f6",
  "borderTop": "2px solid #000",
  "borderRight": "1px solid #ccc",
  "borderBottom": "2px solid #000",
  "borderLeft": "1px solid #ccc",
  "borderWidth": "1px | 2px | 4px",
  "borderStyle": "solid | dashed | dotted | none",
  "borderRadius": "0.25rem | 0.5rem | 0.75rem | 1rem | 50%",
  "borderTopLeftRadius": "0.5rem",
  "borderTopRightRadius": "0.5rem",
  "borderBottomLeftRadius": "0.5rem",
  "borderBottomRightRadius": "0.5rem"
}
```

#### Effects
```json
{
  "boxShadow": "0 1px 3px rgba(0,0,0,0.1) | 0 4px 6px rgba(0,0,0,0.1)",
  "textShadow": "0 2px 4px rgba(0,0,0,0.1)",
  "background": "linear-gradient(to right, #000, #fff) | #ffffff",
  "backgroundImage": "url('/image.jpg')",
  "backgroundSize": "cover | contain | 100% auto",
  "backgroundPosition": "center | top left",
  "backgroundRepeat": "no-repeat | repeat | repeat-x",
  "transform": "rotate(45deg) | scale(1.2) | translate(10px, 20px)",
  "transformOrigin": "center | top left",
  "transition": "all 0.3s ease | opacity 200ms",
  "animation": "spin 1s linear infinite"
}
```

#### Overflow
```json
{
  "overflow": "visible | hidden | scroll | auto",
  "overflowX": "visible | hidden | scroll | auto",
  "overflowY": "visible | hidden | scroll | auto"
}
```

#### Interaction
```json
{
  "cursor": "pointer | move | not-allowed | text | default",
  "pointerEvents": "auto | none",
  "userSelect": "auto | none | text | all"
}
```

---

## Action System

### Action Definition Structure

```typescript
{
  "id": string,              // ✅ Required - Unique action identifier
  "type": ActionType,        // ✅ Required - Action type
  "config": object           // ✅ Required - Action configuration
}
```

### Action Types

#### 1. Navigate Action
```json
{
  "id": "goHome",
  "type": "navigate",
  "config": {
    "url": "/home",
    "openInNewTab": false
  }
}
```

#### 2. API Action
```json
{
  "id": "savePolicy",
  "type": "api",
  "config": {
    "endpoint": "/api/policies",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "status": "draft"
    }
  }
}
```

#### 3. Set State Action
```json
{
  "id": "updateStatus",
  "type": "setState",
  "config": {
    "stateKey": "policyStatus",
    "stateValue": "active"
  }
}
```

#### 4. Submit Action
```json
{
  "id": "submitForm",
  "type": "submit",
  "config": {
    "target": "/api/submit",
    "validation": true
  }
}
```

#### 5. Custom Action
```json
{
  "id": "customHandler",
  "type": "custom",
  "config": {
    "handler": "generatePolicy",
    "params": {
      "template": "standard"
    }
  }
}
```

#### 6. Log Action
```json
{
  "id": "logEvent",
  "type": "log",
  "config": {
    "message": "Button clicked"
  }
}
```

### Triggering Actions

Reference actions by ID in component props:

```json
{
  "type": "button",
  "props": {
    "label": "Save",
    "onClick": "savePolicy"
  }
}

{
  "type": "form",
  "props": {
    "onSubmit": "submitForm"
  }
}
```

---

## Data Binding

### Data Source Structure

```typescript
{
  "id": string,              // ✅ Required - Unique identifier
  "type": "api" | "static" | "computed",  // ✅ Required - Source type
  "config": object           // ✅ Required - Type-specific configuration
}
```

### API Data Source

```json
{
  "dataSources": [
    {
      "id": "policies",
      "type": "api",
      "config": {
        "endpoint": "/api/policies",
        "method": "GET",
        "headers": {
          "Authorization": "Bearer {{token}}"
        }
      }
    }
  ]
}
```

### Static Data Source

```json
{
  "dataSources": [
    {
      "id": "statusOptions",
      "type": "static",
      "config": {
        "data": [
          { "label": "Active", "value": "active" },
          { "label": "Draft", "value": "draft" },
          { "label": "Archived", "value": "archived" }
        ]
      }
    }
  ]
}
```

### Using Data Bindings

Bind data to components using `{{dataSourceId}}`:

```json
{
  "type": "table",
  "props": {
    "columns": [
      { "key": "title", "label": "Title" },
      { "key": "status", "label": "Status" }
    ],
    "data": "{{policies}}"
  }
}

{
  "type": "select",
  "props": {
    "name": "status",
    "label": "Status",
    "options": "{{statusOptions}}"
  }
}
```

---

## Validation Rules

### Must Include
1. `"version": "1.0"` at root level
2. `"components": []` array at root level
3. `"type"` key in every component
4. Required props for each component type (see component reference)

### Must Not Include
1. Undefined component types
2. Invalid CSS property names
3. Non-existent action ID references
4. Circular component nesting
5. Executable code or functions

### Valid Example

```json
{
  "version": "1.0",
  "components": [
    {
      "type": "heading",
      "props": {
        "content": "Dashboard",
        "level": 1
      },
      "css": {
        "fontSize": "2rem",
        "marginBottom": "1.5rem"
      }
    }
  ]
}
```

### Invalid Examples

```json
// ❌ Missing version
{
  "components": []
}

// ❌ Wrong version
{
  "version": "2.0",
  "components": []
}

// ❌ Missing required prop
{
  "version": "1.0",
  "components": [
    {
      "type": "heading",
      "props": {
        "level": 1
      }
    }
  ]
}

// ❌ Invalid component type
{
  "version": "1.0",
  "components": [
    {
      "type": "customButton",
      "props": {}
    }
  ]
}

// ❌ CSS units as numbers
{
  "version": "1.0",
  "components": [
    {
      "type": "container",
      "css": {
        "padding": 2,
        "margin": 1.5
      }
    }
  ]
}
```

---

## Complete Example

```json
{
  "version": "1.0",
  "metadata": {
    "title": "Policy Dashboard",
    "description": "Main policy management interface"
  },
  "actions": [
    {
      "id": "createPolicy",
      "type": "api",
      "config": {
        "endpoint": "/api/policies",
        "method": "POST"
      }
    }
  ],
  "components": [
    {
      "type": "container",
      "props": {
        "maxWidth": "xl",
        "centered": true
      },
      "css": {
        "paddingY": "2rem",
        "paddingX": "1rem"
      },
      "children": [
        {
          "type": "row",
          "props": {
            "justify": "between",
            "align": "center"
          },
          "css": {
            "marginBottom": "2rem"
          },
          "children": [
            {
              "type": "heading",
              "props": {
                "content": "Policy Dashboard",
                "level": 1
              },
              "css": {
                "fontSize": "2rem",
                "fontWeight": "700"
              }
            },
            {
              "type": "button",
              "props": {
                "label": "+ New Policy",
                "variant": "primary",
                "onClick": "createPolicy"
              },
              "css": {
                "paddingX": "1.5rem",
                "paddingY": "0.75rem"
              }
            }
          ]
        },
        {
          "type": "grid",
          "props": {
            "columns": 4,
            "gap": 4
          },
          "css": {
            "display": "grid",
            "gridTemplateColumns": "repeat(4, 1fr)",
            "gap": "1.5rem"
          },
          "children": [
            {
              "type": "card",
              "props": {
                "variant": "elevated"
              },
              "css": {
                "padding": "1.5rem",
                "borderRadius": "0.5rem"
              },
              "children": [
                {
                  "type": "text",
                  "props": {
                    "content": "Total Policies",
                    "variant": "caption"
                  },
                  "css": {
                    "fontSize": "0.875rem",
                    "color": "#6b7280",
                    "marginBottom": "0.5rem"
                  }
                },
                {
                  "type": "heading",
                  "props": {
                    "content": "24",
                    "level": 2
                  },
                  "css": {
                    "fontSize": "2rem",
                    "fontWeight": "700",
                    "color": "#3b82f6"
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

## Output Format Rules

### 1. Output Valid JSON Only
- No markdown code fences
- No explanatory text
- Start with `{` and end with `}`

### 2. Use String Values for CSS Units
```json
{
  "css": {
    "padding": "2rem",      // ✅ Correct
    "margin": "1.5rem",     // ✅ Correct
    "fontSize": "1rem"      // ✅ Correct
  }
}
```

### 3. Include Required Props
Every component type has required props that must be present.

### 4. Use Valid Component Types
Only use component types from the supported list.

### 5. Reference Defined Actions
`onClick` and `onSubmit` props must reference action IDs defined in the `actions` array.

---

## Common Patterns

### Centered Container
```json
{
  "type": "container",
  "props": {
    "maxWidth": "lg",
    "centered": true
  },
  "css": {
    "paddingY": "2rem",
    "paddingX": "1rem"
  },
  "children": []
}
```

### Flex Row with Spacing
```json
{
  "type": "row",
  "props": {
    "justify": "between",
    "align": "center",
    "gap": 4
  },
  "css": {
    "display": "flex",
    "justifyContent": "space-between",
    "alignItems": "center",
    "gap": "1rem"
  },
  "children": []
}
```

### Grid Layout
```json
{
  "type": "grid",
  "props": {
    "columns": 3,
    "gap": 4
  },
  "css": {
    "display": "grid",
    "gridTemplateColumns": "repeat(3, 1fr)",
    "gap": "1.5rem"
  },
  "children": []
}
```

### Form with Inputs
```json
{
  "type": "form",
  "props": {
    "onSubmit": "submitForm"
  },
  "css": {
    "display": "flex",
    "flexDirection": "column",
    "gap": "1.5rem"
  },
  "children": [
    {
      "type": "input",
      "props": {
        "name": "email",
        "label": "Email",
        "type": "email",
        "required": true
      }
    },
    {
      "type": "button",
      "props": {
        "label": "Submit",
        "variant": "primary"
      }
    }
  ]
}
```

---

## Summary

**Key Points:**
1. Always include `"version": "1.0"` and `"components": []`
2. Use string values for all CSS units: `"1rem"`, `"16px"`, `"100%"`
3. Include required props for each component type
4. Reference actions by ID in `onClick` and `onSubmit` props
5. Use only supported component types (35 types available)
6. Output pure JSON without markdown or explanations



7. Visual Polish and Styling Quality

7.1 Create a Professional, Attractive Interface

Generate a polished, modern, professional UI rather than a plain document layout.

Use a consistent color palette appropriate for the policy's purpose.

Use subtle background colors, borders, rounded corners, and shadows where supported.

Make the policy title visually prominent with appropriate typography and spacing.

Use cards or other supported containers to visually group related policy information.

Make long policy sections easy to scan using clearly styled headings, lists, and accordions.

7.2 Use CSS Deliberately

Use the css object to apply visual styling wherever the schema and renderer support it.

Prefer a restrained palette, such as a primary blue, neutral backgrounds, readable dark text, and subtle borders.

Use valid CSS values with the correct data types.

Apply consistent spacing, padding, margins, font sizes, font weights, and border radii.

Use contrasting text and background colors to maintain readability.

Avoid adding arbitrary CSS properties that are not supported by the renderer.

Do not rely on props for styling when the schema defines a separate css object.

7.3 Style Policy Sections

Use the most suitable supported component for each section.

Use accordions for long sections when the schema supports them.

Give section headings sufficient visual distinction.

Use readable paragraph spacing and well-structured lists.

Use subtle borders or backgrounds to separate sections when appropriate.

Avoid excessive colors, unnecessary decoration, and overly dense layouts.

7.4 Final Visual Quality Check

Before returning the JSON, verify that:

The page has a clear visual hierarchy.

The title and section headings are visually distinct.

Supported CSS styling is included where it improves readability.

The color palette and spacing are consistent.

All styling uses properties supported by the schema and renderer.

The UI remains readable and usable on smaller screens.

The result is valid JSON and preserves the source policy's meaning.