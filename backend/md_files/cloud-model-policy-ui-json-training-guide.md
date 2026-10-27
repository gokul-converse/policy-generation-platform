# Cloud Model Policy UI JSON Training Guide

## Executive Summary

This guide trains cloud models to generate production-quality, realistic, interactive policy UI JSON schemas. The model dynamically selects appropriate layouts, components, and styling based on each policy's content, complexity, and purpose—not from predefined templates.

**Key Capabilities:**
- ✅ Dynamic UI generation based on policy content
- ✅ Responsive layouts with grids, columns, and cards
- ✅ Rich typography and visual hierarchy
- ✅ Interactive components (forms, tabs, accordions, tables)
- ✅ Professional color systems and spacing
- ✅ Semantic HTML structure
- ✅ Accessibility compliance

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Root Schema Structure](#root-schema-structure)
3. [Component Registry](#component-registry)
4. [Layout Design Patterns](#layout-design-patterns)
5. [Typography & Visual Hierarchy](#typography--visual-hierarchy)
6. [Color & Styling System](#color--styling-system)
7. [Interactive Components](#interactive-components)
8. [Policy-Specific Patterns](#policy-specific-patterns)
9. [Production Example](#production-example)
10. [Cloud Model Prompt](#cloud-model-prompt)
11. [Validation & Error Handling](#validation--error-handling)

---

## Core Principles

### 1. Dynamic Content-Driven Design

**Don't**: Use fixed templates regardless of policy content
**Do**: Analyze policy structure and select appropriate components

```
Policy with many sections → Use accordion or tabs
Policy with steps/process → Use numbered list or stepper
Policy with data/metrics → Use table or grid cards
Policy with forms → Use interactive form components
```

### 2. Visual Hierarchy

Establish clear information hierarchy:
- **Level 1**: Policy title (h1, 2-3rem, bold)
- **Level 2**: Major sections (h2, 1.5-2rem, semibold)
- **Level 3**: Subsections (h3, 1.25-1.5rem, medium)
- **Level 4**: Sub-subsections (h4, 1.125rem, medium)
- **Body**: Regular text (1rem, normal)
- **Captions**: Helper text (0.875rem, light)

### 3. Responsive Layout

Use flexible layouts that adapt to content:
- **Container**: Max-width constraints (sm: 640px, md: 768px, lg: 1024px, xl: 1280px)
- **Grid**: Auto-responsive columns (1 col mobile, 2-3 cols desktop)
- **Stack**: Vertical spacing with consistent gaps
- **Row**: Horizontal layouts with flex properties

### 4. Spacing System

Consistent spacing scale (in rem):
- **0.25rem** (4px): Tight spacing
- **0.5rem** (8px): Minimal spacing
- **1rem** (16px): Standard spacing
- **1.5rem** (24px): Comfortable spacing
- **2rem** (32px): Section spacing
- **3rem** (48px): Major section breaks
- **4rem** (64px): Page sections

---

## Root Schema Structure

### Required Structure

```json
{
  "version": "1.0",
  "metadata": {
    "title": "Policy Document Title",
    "description": "Brief description of the policy",
    "author": "Organization or System Name",
    "createdAt": "ISO 8601 timestamp"
  },
  "components": [
    // UI components here
  ]
}
```

### Metadata Guidelines

- **title**: Clear, descriptive policy name
- **description**: One-sentence purpose statement
- **author**: Organization or system identifier
- **createdAt**: ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)

---

## Component Registry

### Layout Components

| Component | Purpose | Children | Key Props |
|-----------|---------|----------|-----------|
| `container` | Page/section wrapper | Yes | `maxWidth`, `centered`, `padding` |
| `grid` | Multi-column layouts | Yes | `columns`, `gap` |
| `row` | Horizontal layouts | Yes | `justify`, `align`, `gap` |
| `column` | Vertical sections | Yes | `span`, `gap` |
| `stack` | Vertical stacking | Yes | `direction`, `gap` |
| `card` | Bordered containers | Yes | `title`, `subtitle`, `variant` |
| `spacer` | Empty space | No | `size` |
| `divider` | Visual separator | No | None |

### Typography Components

| Component | Purpose | Children | Key Props |
|-----------|---------|----------|-----------|
| `heading` | Headings (h1-h6) | No | `content`, `level`, `size` |
| `text` | Body text | No | `content`, `variant`, `size`, `weight` |
| `paragraph` | Paragraph text | No | `content` |
| `link` | Hyperlinks | No | `content`, `href`, `target` |

### Form Components

| Component | Purpose | Children | Key Props |
|-----------|---------|----------|-----------|
| `form` | Form container | Yes | `onSubmit` |
| `input` | Text input | No | `name`, `type`, `label`, `placeholder` |
| `textarea` | Multi-line input | No | `name`, `label`, `rows` |
| `select` | Dropdown | No | `name`, `options`, `label` |
| `checkbox` | Checkbox | No | `name`, `label`, `checked` |
| `radio` | Radio button | No | `name`, `value`, `label` |
| `button` | Button | No | `label`, `variant`, `onClick` |

### Interactive Components

| Component | Purpose | Children | Key Props |
|-----------|---------|----------|-----------|
| `tabs` | Tabbed interface | No (uses `items`) | `items` (array of {id, label, content}) |
| `accordion` | Collapsible sections | No (uses `items`) | `items` (array of {id, title, content}) |
| `table` | Data tables | No | `columns`, `data` |
| `list` | Lists | No | `items` (array of {id, content}), `variant` |
| `alert` | Notifications | No | `message`, `variant`, `title` |
| `badge` | Status indicators | No | `label`, `variant` |
| `breadcrumb` | Navigation trail | No | `items` (array of {label, href}) |

---

## Layout Design Patterns

### Pattern 1: Centered Document Layout

**Use for**: Traditional policy documents, formal content

```json
{
  "type": "container",
  "props": {
    "maxWidth": "lg",
    "centered": true,
    "padding": 8
  },
  "children": [
    {
      "type": "stack",
      "props": {
        "direction": "vertical",
        "gap": 6
      },
      "children": [
        // Header
        {
          "type": "heading",
          "props": {
            "content": "Employee Annual Leave Policy",
            "level": 1,
            "size": "xl"
          }
        },
        // Metadata
        {
          "type": "row",
          "props": {
            "gap": 4,
            "justify": "between"
          },
          "children": [
            {
              "type": "text",
              "props": {
                "content": "Effective Date: January 1, 2024",
                "size": "sm",
                "variant": "caption"
              }
            },
            {
              "type": "badge",
              "props": {
                "label": "Version 2.0",
                "variant": "info"
              }
            }
          ]
        },
        {
          "type": "divider"
        },
        // Content sections follow
      ]
    }
  ]
}
```

### Pattern 2: Multi-Column Grid Layout

**Use for**: Policies with multiple parallel sections, comparison layouts

```json
{
  "type": "container",
  "props": {
    "maxWidth": "xl",
    "padding": 8
  },
  "children": [
    {
      "type": "grid",
      "props": {
        "columns": 3,
        "gap": 6
      },
      "children": [
        {
          "type": "card",
          "props": {
            "title": "Employee Rights",
            "variant": "bordered"
          },
          "children": [/* content */]
        },
        {
          "type": "card",
          "props": {
            "title": "Employer Responsibilities",
            "variant": "bordered"
          },
          "children": [/* content */]
        },
        {
          "type": "card",
          "props": {
            "title": "Reporting Procedures",
            "variant": "bordered"
          },
          "children": [/* content */]
        }
      ]
    }
  ]
}
```

### Pattern 3: Sidebar + Content Layout

**Use for**: Policies with navigation, table of contents

```json
{
  "type": "container",
  "props": {
    "maxWidth": "full",
    "padding": 0
  },
  "children": [
    {
      "type": "grid",
      "props": {
        "columns": "250px 1fr",
        "gap": 0
      },
      "children": [
        {
          "type": "card",
          "props": {
            "className": "h-screen sticky top-0 rounded-none border-r"
          },
          "children": [/* Sidebar navigation */]
        },
        {
          "type": "container",
          "props": {
            "padding": 8
          },
          "children": [/* Main content */]
        }
      ]
    }
  ]
}
```

### Pattern 4: Dashboard/Summary View

**Use for**: Policy overviews, metrics, quick reference

```json
{
  "type": "container",
  "props": {
    "maxWidth": "xl",
    "padding": 8
  },
  "children": [
    {
      "type": "stack",
      "props": {
        "gap": 6
      },
      "children": [
        // Metrics cards
        {
          "type": "grid",
          "props": {
            "columns": 4,
            "gap": 4
          },
          "children": [
            {
              "type": "card",
              "props": {
                "variant": "elevated",
                "padding": 6
              },
              "children": [
                {
                  "type": "stack",
                  "props": {
                    "gap": 2
                  },
                  "children": [
                    {
                      "type": "text",
                      "props": {
                        "content": "25 Days",
                        "size": "2xl",
                        "weight": "bold"
                      }
                    },
                    {
                      "type": "text",
                      "props": {
                        "content": "Annual Leave",
                        "size": "sm",
                        "variant": "caption"
                      }
                    }
                  ]
                }
              ]
            }
            // More metric cards...
          ]
        }
      ]
    }
  ]
}
```

---

## Typography & Visual Hierarchy

### Heading System

```json
// Policy Title (H1)
{
  "type": "heading",
  "props": {
    "content": "Main Policy Title",
    "level": 1,
    "size": "3xl"
  }
}

// Major Section (H2)
{
  "type": "heading",
  "props": {
    "content": "1. Purpose and Scope",
    "level": 2,
    "size": "2xl"
  }
}

// Subsection (H3)
{
  "type": "heading",
  "props": {
    "content": "1.1 Application",
    "level": 3,
    "size": "xl"
  }
}

// Minor Heading (H4)
{
  "type": "heading",
  "props": {
    "content": "Eligibility Criteria",
    "level": 4,
    "size": "lg"
  }
}
```

### Text Variants

```json
// Body Text
{
  "type": "text",
  "props": {
    "content": "Regular policy text content.",
    "size": "base",
    "weight": "normal"
  }
}

// Emphasized Text
{
  "type": "text",
  "props": {
    "content": "Important policy statement.",
    "size": "base",
    "weight": "semibold"
  }
}

// Caption/Helper Text
{
  "type": "text",
  "props": {
    "content": "Last updated: January 2024",
    "size": "sm",
    "variant": "caption"
  }
}

// Legal/Fine Print
{
  "type": "text",
  "props": {
    "content": "This policy supersedes all previous versions.",
    "size": "xs",
    "variant": "caption"
  }
}
```

---

## Color & Styling System

### Color Variants

**Primary Colors** (Blue): Brand actions, primary CTAs
**Secondary Colors** (Gray): Supporting elements
**Success** (Green): Approvals, positive states
**Danger** (Red): Warnings, restrictions, errors
**Warning** (Yellow/Orange): Cautions, pending items
**Info** (Cyan/Blue): Information, notes
**Muted** (Gray): Disabled, inactive states

### Component Styling

```json
// Alert Usage
{
  "type": "alert",
  "props": {
    "variant": "warning",
    "title": "Important Notice",
    "message": "This policy is mandatory for all employees."
  }
}

// Badge Usage
{
  "type": "badge",
  "props": {
    "label": "Required",
    "variant": "danger"
  }
}

// Button Variants
{
  "type": "button",
  "props": {
    "label": "Submit Request",
    "variant": "primary",  // primary, secondary, success, danger, ghost
    "size": "md"           // xs, sm, md, lg, xl
  }
}
```

### Card Styling

```json
// Elevated Card (default)
{
  "type": "card",
  "props": {
    "variant": "elevated",
    "padding": 6
  }
}

// Bordered Card
{
  "type": "card",
  "props": {
    "variant": "bordered",
    "hoverable": true,
    "padding": 6
  }
}

// Card with Header
{
  "type": "card",
  "props": {
    "title": "Section Title",
    "subtitle": "Optional description",
    "variant": "bordered"
  },
  "children": [/* Content */]
}
```

---

## Interactive Components

### Lists (CRITICAL FORMAT)

**ALWAYS use object format with `id` and `content`**:

```json
{
  "type": "list",
  "props": {
    "variant": "numbered",  // plain, bullet, numbered
    "items": [
      {
        "id": "item-1",
        "content": "Submit leave request at least 2 weeks in advance"
      },
      {
        "id": "item-2",
        "content": "Manager reviews and responds within 2 days"
      },
      {
        "id": "item-3",
        "content": "Receive confirmation email upon approval"
      }
    ]
  }
}
```

❌ **NEVER use string arrays** - this causes errors:
```json
{
  "props": {
    "items": ["Item 1", "Item 2"]  // WRONG
  }
}
```

### Tables

```json
{
  "type": "table",
  "props": {
    "columns": [
      {
        "key": "leave_type",
        "label": "Leave Type",
        "width": "200px"
      },
      {
        "key": "days",
        "label": "Days Allowed",
        "align": "center"
      },
      {
        "key": "approval",
        "label": "Approval Required",
        "align": "center"
      }
    ],
    "data": [
      {
        "leave_type": "Annual Leave",
        "days": "25",
        "approval": "Manager"
      },
      {
        "leave_type": "Sick Leave",
        "days": "10",
        "approval": "Self-certified"
      },
      {
        "leave_type": "Parental Leave",
        "days": "18 weeks",
        "approval": "HR Department"
      }
    ],
    "striped": true,
    "hoverable": true
  }
}
```

### Accordions

```json
{
  "type": "accordion",
  "props": {
    "items": [
      {
        "id": "section-1",
        "title": "Eligibility Requirements",
        "content": {
          "type": "stack",
          "props": { "gap": 3 },
          "children": [
            {
              "type": "text",
              "props": {
                "content": "All full-time employees are eligible after completing 3 months of service."
              }
            },
            {
              "type": "list",
              "props": {
                "variant": "bullet",
                "items": [
                  {
                    "id": "req-1",
                    "content": "Minimum 3 months service"
                  },
                  {
                    "id": "req-2",
                    "content": "Full-time employment status"
                  },
                  {
                    "id": "req-3",
                    "content": "Active employee record"
                  }
                ]
              }
            }
          ]
        }
      },
      {
        "id": "section-2",
        "title": "Application Process",
        "content": {
          "type": "text",
          "props": {
            "content": "Submit requests through the HR portal..."
          }
        }
      }
    ]
  }
}
```

### Tabs

```json
{
  "type": "tabs",
  "props": {
    "items": [
      {
        "id": "overview",
        "label": "Overview",
        "content": {
          "type": "stack",
          "props": { "gap": 4 },
          "children": [/* Overview content */]
        }
      },
      {
        "id": "details",
        "label": "Detailed Requirements",
        "content": {
          "type": "stack",
          "props": { "gap": 4 },
          "children": [/* Details content */]
        }
      },
      {
        "id": "faq",
        "label": "FAQ",
        "content": {
          "type": "accordion",
          "props": {
            "items": [/* FAQ items */]
          }
        }
      }
    ]
  }
}
```

### Forms

```json
{
  "type": "form",
  "props": {
    "onSubmit": "submitLeaveRequest"
  },
  "children": [
    {
      "type": "stack",
      "props": { "gap": 4 },
      "children": [
        {
          "type": "input",
          "props": {
            "name": "employee_name",
            "type": "text",
            "label": "Employee Name",
            "placeholder": "Enter your full name",
            "required": true
          }
        },
        {
          "type": "select",
          "props": {
            "name": "leave_type",
            "label": "Leave Type",
            "options": [
              { "value": "annual", "label": "Annual Leave" },
              { "value": "sick", "label": "Sick Leave" },
              { "value": "parental", "label": "Parental Leave" }
            ],
            "required": true
          }
        },
        {
          "type": "textarea",
          "props": {
            "name": "reason",
            "label": "Reason for Leave",
            "placeholder": "Provide details...",
            "rows": 4
          }
        },
        {
          "type": "row",
          "props": {
            "justify": "end",
            "gap": 3
          },
          "children": [
            {
              "type": "button",
              "props": {
                "label": "Cancel",
                "variant": "ghost"
              }
            },
            {
              "type": "button",
              "props": {
                "label": "Submit Request",
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
```

---

## Policy-Specific Patterns

### Pattern: HR Policy (Leave, Benefits)

```json
{
  "type": "container",
  "props": { "maxWidth": "lg", "padding": 8 },
  "children": [
    {
      "type": "stack",
      "props": { "gap": 6 },
      "children": [
        // Header with badge
        {
          "type": "row",
          "props": { "justify": "between", "align": "center" },
          "children": [
            {
              "type": "heading",
              "props": { "content": "Annual Leave Policy", "level": 1 }
            },
            {
              "type": "badge",
              "props": { "label": "Effective 2024", "variant": "info" }
            }
          ]
        },
        // Summary cards
        {
          "type": "grid",
          "props": { "columns": 3, "gap": 4 },
          "children": [
            {
              "type": "card",
              "props": { "variant": "bordered", "padding": 6 },
              "children": [
                {
                  "type": "stack",
                  "props": { "gap": 2 },
                  "children": [
                    {
                      "type": "text",
                      "props": { "content": "25 Days", "size": "2xl", "weight": "bold" }
                    },
                    {
                      "type": "text",
                      "props": { "content": "Annual Entitlement", "size": "sm", "variant": "caption" }
                    }
                  ]
                }
              ]
            }
            // More cards...
          ]
        },
        // Content sections
        {
          "type": "accordion",
          "props": {
            "items": [/* Policy sections */]
          }
        }
      ]
    }
  ]
}
```

### Pattern: Security Policy

```json
{
  "type": "container",
  "props": { "maxWidth": "xl", "padding": 8 },
  "children": [
    {
      "type": "stack",
      "props": { "gap": 8 },
      "children": [
        // Alert banner
        {
          "type": "alert",
          "props": {
            "variant": "danger",
            "title": "Mandatory Compliance",
            "message": "All employees must comply with this security policy."
          }
        },
        // Requirements table
        {
          "type": "card",
          "props": { "title": "Security Requirements" },
          "children": [
            {
              "type": "table",
              "props": {
                "columns": [
                  { "key": "requirement", "label": "Requirement" },
                  { "key": "level", "label": "Level", "align": "center" },
                  { "key": "penalty", "label": "Non-Compliance", "align": "center" }
                ],
                "data": [/* Table data */],
                "striped": true
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### Pattern: Code of Conduct

```json
{
  "type": "container",
  "props": { "maxWidth": "lg", "padding": 8 },
  "children": [
    {
      "type": "stack",
      "props": { "gap": 6 },
      "children": [
        // Principles grid
        {
          "type": "grid",
          "props": { "columns": 2, "gap": 6 },
          "children": [
            {
              "type": "card",
              "props": {
                "title": "Core Values",
                "variant": "bordered"
              },
              "children": [
                {
                  "type": "list",
                  "props": {
                    "variant": "bullet",
                    "items": [
                      { "id": "v1", "content": "Integrity" },
                      { "id": "v2", "content": "Respect" },
                      { "id": "v3", "content": "Accountability" }
                    ]
                  }
                }
              ]
            },
            {
              "type": "card",
              "props": {
                "title": "Expected Behaviors",
                "variant": "bordered"
              },
              "children": [/* Content */]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Production Example

### Complete Policy Document

```json
{
  "version": "1.0",
  "metadata": {
    "title": "Employee Remote Work Policy",
    "description": "Guidelines and requirements for remote work arrangements",
    "author": "HR Department",
    "createdAt": "2024-01-20T00:00:00Z"
  },
  "components": [
    {
      "type": "container",
      "props": {
        "maxWidth": "xl",
        "padding": 8
      },
      "children": [
        {
          "type": "stack",
          "props": {
            "direction": "vertical",
            "gap": 8
          },
          "children": [
            {
              "type": "card",
              "props": {
                "variant": "elevated",
                "padding": 6
              },
              "children": [
                {
                  "type": "stack",
                  "props": { "gap": 4 },
                  "children": [
                    {
                      "type": "row",
                      "props": {
                        "justify": "between",
                        "align": "center"
                      },
                      "children": [
                        {
                          "type": "heading",
                          "props": {
                            "content": "Remote Work Policy",
                            "level": 1,
                            "size": "3xl"
                          }
                        },
                        {
                          "type": "badge",
                          "props": {
                            "label": "Version 2.0",
                            "variant": "info"
                          }
                        }
                      ]
                    },
                    {
                      "type": "text",
                      "props": {
                        "content": "Comprehensive guidelines for flexible work arrangements",
                        "size": "lg",
                        "variant": "caption"
                      }
                    },
                    {
                      "type": "row",
                      "props": { "gap": 6 },
                      "children": [
                        {
                          "type": "text",
                          "props": {
                            "content": "Effective: January 1, 2024",
                            "size": "sm",
                            "variant": "caption"
                          }
                        },
                        {
                          "type": "text",
                          "props": {
                            "content": "Review Date: December 31, 2024",
                            "size": "sm",
                            "variant": "caption"
                          }
                        }
                      ]
                    }
                  ]
                }
              ]
            },
            {
              "type": "alert",
              "props": {
                "variant": "info",
                "title": "Policy Scope",
                "message": "This policy applies to all employees eligible for remote work arrangements."
              }
            },
            {
              "type": "grid",
              "props": {
                "columns": 4,
                "gap": 4
              },
              "children": [
                {
                  "type": "card",
                  "props": {
                    "variant": "bordered",
                    "padding": 6,
                    "hoverable": true
                  },
                  "children": [
                    {
                      "type": "stack",
                      "props": { "gap": 2 },
                      "children": [
                        {
                          "type": "text",
                          "props": {
                            "content": "3 days/week",
                            "size": "2xl",
                            "weight": "bold"
                          }
                        },
                        {
                          "type": "text",
                          "props": {
                            "content": "Maximum Remote Days",
                            "size": "sm",
                            "variant": "caption"
                          }
                        }
                      ]
                    }
                  ]
                },
                {
                  "type": "card",
                  "props": {
                    "variant": "bordered",
                    "padding": 6,
                    "hoverable": true
                  },
                  "children": [
                    {
                      "type": "stack",
                      "props": { "gap": 2 },
                      "children": [
                        {
                          "type": "text",
                          "props": {
                            "content": "3 months",
                            "size": "2xl",
                            "weight": "bold"
                          }
                        },
                        {
                          "type": "text",
                          "props": {
                            "content": "Minimum Service",
                            "size": "sm",
                            "variant": "caption"
                          }
                        }
                      ]
                    }
                  ]
                },
                {
                  "type": "card",
                  "props": {
                    "variant": "bordered",
                    "padding": 6,
                    "hoverable": true
                  },
                  "children": [
                    {
                      "type": "stack",
                      "props": { "gap": 2 },
                      "children": [
                        {
                          "type": "text",
                          "props": {
                            "content": "$500",
                            "size": "2xl",
                            "weight": "bold"
                          }
                        },
                        {
                          "type": "text",
                          "props": {
                            "content": "Equipment Budget",
                            "size": "sm",
                            "variant": "caption"
                          }
                        }
                      ]
                    }
                  ]
                },
                {
                  "type": "card",
                  "props": {
                    "variant": "bordered",
                    "padding": 6,
                    "hoverable": true
                  },
                  "children": [
                    {
                      "type": "stack",
                      "props": { "gap": 2 },
                      "children": [
                        {
                          "type": "text",
                          "props": {
                            "content": "24/7",
                            "size": "2xl",
                            "weight": "bold"
                          }
                        },
                        {
                          "type": "text",
                          "props": {
                            "content": "IT Support Access",
                            "size": "sm",
                            "variant": "caption"
                          }
                        }
                      ]
                    }
                  ]
                }
              ]
            },
            {
              "type": "divider"
            },
            {
              "type": "tabs",
              "props": {
                "items": [
                  {
                    "id": "overview",
                    "label": "Overview",
                    "content": {
                      "type": "stack",
                      "props": { "gap": 6 },
                      "children": [
                        {
                          "type": "heading",
                          "props": {
                            "content": "1. Purpose and Objectives",
                            "level": 2
                          }
                        },
                        {
                          "type": "text",
                          "props": {
                            "content": "This policy establishes guidelines for employees to work remotely while maintaining productivity, collaboration, and security standards."
                          }
                        },
                        {
                          "type": "card",
                          "props": {
                            "title": "Key Objectives",
                            "variant": "bordered",
                            "padding": 6
                          },
                          "children": [
                            {
                              "type": "list",
                              "props": {
                                "variant": "bullet",
                                "items": [
                                  {
                                    "id": "obj-1",
                                    "content": "Provide flexibility to employees while maintaining business operations"
                                  },
                                  {
                                    "id": "obj-2",
                                    "content": "Ensure data security and compliance with company policies"
                                  },
                                  {
                                    "id": "obj-3",
                                    "content": "Maintain team collaboration and communication standards"
                                  },
                                  {
                                    "id": "obj-4",
                                    "content": "Support work-life balance and employee well-being"
                                  }
                                ]
                              }
                            }
                          ]
                        }
                      ]
                    }
                  },
                  {
                    "id": "eligibility",
                    "label": "Eligibility",
                    "content": {
                      "type": "stack",
                      "props": { "gap": 6 },
                      "children": [
                        {
                          "type": "heading",
                          "props": {
                            "content": "2. Eligibility Requirements",
                            "level": 2
                          }
                        },
                        {
                          "type": "grid",
                          "props": {
                            "columns": 2,
                            "gap": 4
                          },
                          "children": [
                            {
                              "type": "card",
                              "props": {
                                "title": "Eligible Employees",
                                "variant": "bordered",
                                "padding": 6
                              },
                              "children": [
                                {
                                  "type": "list",
                                  "props": {
                                    "variant": "bullet",
                                    "items": [
                                      {
                                        "id": "elig-1",
                                        "content": "Full-time employees with minimum 3 months service"
                                      },
                                      {
                                        "id": "elig-2",
                                        "content": "Satisfactory performance reviews"
                                      },
                                      {
                                        "id": "elig-3",
                                        "content": "Role compatible with remote work"
                                      },
                                      {
                                        "id": "elig-4",
                                        "content": "Manager approval obtained"
                                      }
                                    ]
                                  }
                                }
                              ]
                            },
                            {
                              "type": "card",
                              "props": {
                                "title": "Ineligible Employees",
                                "variant": "bordered",
                                "padding": 6
                              },
                              "children": [
                                {
                                  "type": "list",
                                  "props": {
                                    "variant": "bullet",
                                    "items": [
                                      {
                                        "id": "inelig-1",
                                        "content": "Employees on probation"
                                      },
                                      {
                                        "id": "inelig-2",
                                        "content": "Roles requiring on-site presence"
                                      },
                                      {
                                        "id": "inelig-3",
                                        "content": "Active performance improvement plans"
                                      },
                                      {
                                        "id": "inelig-4",
                                        "content": "Security clearance restrictions"
                                      }
                                    ]
                                  }
                                }
                              ]
                            }
                          ]
                        }
                      ]
                    }
                  },
                  {
                    "id": "requirements",
                    "label": "Requirements",
                    "content": {
                      "type": "stack",
                      "props": { "gap": 6 },
                      "children": [
                        {
                          "type": "heading",
                          "props": {
                            "content": "3. Equipment and Technical Requirements",
                            "level": 2
                          }
                        },
                        {
                          "type": "card",
                          "props": {
                            "title": "Required Equipment",
                            "variant": "elevated"
                          },
                          "children": [
                            {
                              "type": "table",
                              "props": {
                                "columns": [
                                  {
                                    "key": "item",
                                    "label": "Item"
                                  },
                                  {
                                    "key": "specification",
                                    "label": "Specification"
                                  },
                                  {
                                    "key": "provided_by",
                                    "label": "Provided By",
                                    "align": "center"
                                  }
                                ],
                                "data": [
                                  {
                                    "item": "Laptop/Desktop",
                                    "specification": "Company-issued, encrypted",
                                    "provided_by": "Company"
                                  },
                                  {
                                    "item": "Internet Connection",
                                    "specification": "Min. 25 Mbps download",
                                    "provided_by": "Employee"
                                  },
                                  {
                                    "item": "VPN Access",
                                    "specification": "Company VPN client",
                                    "provided_by": "Company"
                                  },
                                  {
                                    "item": "Workspace",
                                    "specification": "Quiet, dedicated area",
                                    "provided_by": "Employee"
                                  },
                                  {
                                    "item": "Monitor (optional)",
                                    "specification": "External display",
                                    "provided_by": "Budget allowance"
                                  }
                                ],
                                "striped": true,
                                "hoverable": true
                              }
                            }
                          ]
                        }
                      ]
                    }
                  },
                  {
                    "id": "procedures",
                    "label": "Procedures",
                    "content": {
                      "type": "stack",
                      "props": { "gap": 6 },
                      "children": [
                        {
                          "type": "heading",
                          "props": {
                            "content": "4. Application and Approval Process",
                            "level": 2
                          }
                        },
                        {
                          "type": "accordion",
                          "props": {
                            "items": [
                              {
                                "id": "step-1",
                                "title": "Step 1: Submit Request",
                                "content": {
                                  "type": "stack",
                                  "props": { "gap": 3 },
                                  "children": [
                                    {
                                      "type": "text",
                                      "props": {
                                        "content": "Complete the Remote Work Request Form available on the HR portal."
                                      }
                                    },
                                    {
                                      "type": "list",
                                      "props": {
                                        "variant": "numbered",
                                        "items": [
                                          {
                                            "id": "submit-1",
                                            "content": "Log in to HR Self-Service Portal"
                                          },
                                          {
                                            "id": "submit-2",
                                            "content": "Navigate to 'Work Arrangements'"
                                          },
                                          {
                                            "id": "submit-3",
                                            "content": "Complete Remote Work Request Form"
                                          },
                                          {
                                            "id": "submit-4",
                                            "content": "Specify proposed schedule and location"
                                          }
                                        ]
                                      }
                                    }
                                  ]
                                }
                              },
                              {
                                "id": "step-2",
                                "title": "Step 2: Manager Review",
                                "content": {
                                  "type": "text",
                                  "props": {
                                    "content": "Your manager will review the request within 3 business days and assess feasibility based on role requirements, team needs, and business operations."
                                  }
                                }
                              },
                              {
                                "id": "step-3",
                                "title": "Step 3: HR Approval",
                                "content": {
                                  "type": "text",
                                  "props": {
                                    "content": "HR will conduct final review and approval, ensuring compliance with policy requirements and completing necessary documentation."
                                  }
                                }
                              },
                              {
                                "id": "step-4",
                                "title": "Step 4: Setup and Training",
                                "content": {
                                  "type": "text",
                                  "props": {
                                    "content": "IT will provision required equipment and access. Employees must complete remote work security training before starting."
                                  }
                                }
                              }
                            ]
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            },
            {
              "type": "divider"
            },
            {
              "type": "card",
              "props": {
                "title": "Need Help?",
                "variant": "bordered",
                "padding": 6
              },
              "children": [
                {
                  "type": "stack",
                  "props": { "gap": 4 },
                  "children": [
                    {
                      "type": "text",
                      "props": {
                        "content": "Contact the HR Department for questions about this policy or to request accommodations."
                      }
                    },
                    {
                      "type": "row",
                      "props": { "gap": 3 },
                      "children": [
                        {
                          "type": "button",
                          "props": {
                            "label": "Contact HR",
                            "variant": "primary"
                          }
                        },
                        {
                          "type": "button",
                          "props": {
                            "label": "Submit Request",
                            "variant": "secondary"
                          }
                        },
                        {
                          "type": "button",
                          "props": {
                            "label": "View FAQ",
                            "variant": "ghost"
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
      ]
    }
  ]
}
```

---

## Cloud Model Prompt

### System Prompt for Policy UI Generation

```
You are a policy UI generation system that creates production-quality, interactive UI JSON schemas from policy content.

CORE RESPONSIBILITIES:
1. Analyze policy content and structure
2. Select appropriate layouts and components dynamically
3. Create professional, accessible, responsive UIs
4. Follow JSON schema specifications exactly
5. Generate semantic, well-organized interfaces

DESIGN PRINCIPLES:
- Use responsive layouts (grids, flexbox, stacks)
- Establish clear visual hierarchy (h1 > h2 > h3 > body > caption)
- Apply consistent spacing (0.5rem, 1rem, 1.5rem, 2rem, 3rem, 4rem)
- Choose appropriate interactive components (tabs, accordions, tables, forms)
- Use color variants meaningfully (primary, danger, warning, info, success)
- Create scannable, digestible content layouts
- Add navigational aids (breadcrumbs, TOC, tabs)

COMPONENT SELECTION LOGIC:
- Many sections (>5) → Tabs or Accordion
- Processes/steps → Numbered lists or Accordion with steps
- Data/metrics → Tables or Grid of cards
- Requirements/rules → Lists (bullet/numbered) with proper object format
- Forms/applications → Interactive form components
- Summaries → Grid of metric cards
- Comparisons → Multi-column grid or table

CRITICAL FORMAT REQUIREMENTS:
1. Version MUST be "1.0"
2. List items MUST be objects: {"id": "unique", "content": "text"}
3. CSS values MUST be strings with units: "1rem", "16px", "100%"
4. Component types MUST match registry exactly (lowercase)
5. Required props MUST be present for each component

AVOID:
- Fixed templates regardless of content
- String arrays in lists (use object format)
- Numeric CSS values (use strings with units)
- Non-standard CSS properties (paddingY, paddingX, marginY, marginX)
- Invalid component types
- Missing required props

OUTPUT FORMAT:
Generate valid JSON only. No markdown, no explanations, just the JSON schema.
```

### Example User Prompt

```
Generate a comprehensive UI for an employee data privacy policy including:
- Policy overview and key requirements
- Data collection and usage sections
- Employee rights and responsibilities
- Procedures for data access requests
- Contact information and resources

Make it professional, scannable, and interactive with appropriate navigation.
```

---

## Validation & Error Handling

### Common Errors to Avoid

#### Error 1: String Arrays in Lists ❌

**Wrong:**
```json
{
  "type": "list",
  "props": {
    "items": ["Item 1", "Item 2"]
  }
}
```

**Correct:**
```json
{
  "type": "list",
  "props": {
    "items": [
      {"id": "item-1", "content": "Item 1"},
      {"id": "item-2", "content": "Item 2"}
    ]
  }
}
```

#### Error 2: Invalid CSS Properties ❌

**Wrong:**
```json
{
  "type": "container",
  "props": {},
  "css": {
    "paddingY": "2rem",
    "paddingX": "1rem"
  }
}
```

**Correct:**
```json
{
  "type": "container",
  "props": {},
  "styles": {
    "paddingTop": "2rem",
    "paddingBottom": "2rem",
    "paddingLeft": "1rem",
    "paddingRight": "1rem"
  }
}
```

Or use shorthand:
```json
{
  "type": "container",
  "props": {},
  "styles": {
    "padding": "2rem 1rem"
  }
}
```

#### Error 3: Numeric CSS Values ❌

**Wrong:**
```json
{
  "styles": {
    "padding": 16,
    "margin": 2
  }
}
```

**Correct:**
```json
{
  "styles": {
    "padding": "16px",
    "margin": "2rem"
  }
}
```

#### Error 4: Invalid Component Types ❌

**Wrong:**
```json
{
  "type": "CustomButton"
}
```

**Correct:**
```json
{
  "type": "button",
  "props": {
    "label": "Click Me"
  }
}
```

#### Error 5: Missing Required Props ❌

**Wrong:**
```json
{
  "type": "heading",
  "props": {
    "level": 1
  }
}
```

**Correct:**
```json
{
  "type": "heading",
  "props": {
    "content": "My Heading",
    "level": 1
  }
}
```

### Validation Checklist

✅ Version is "1.0"  
✅ All list items are objects with `id` and `content`  
✅ CSS values are strings with units  
✅ Component types are lowercase and valid  
✅ Required props present for all components  
✅ Nested structures properly formatted  
✅ Actions properly configured  
✅ Responsive layouts used  
✅ Visual hierarchy established  
✅ Accessibility considered  

---

## Summary & Limitations

### What This Guide Achieves

✅ **Dynamic UI generation** based on policy content  
✅ **Professional layouts** with grids, columns, and responsive design  
✅ **Rich typography** and visual hierarchy  
✅ **Interactive components** (tabs, accordions, forms, tables)  
✅ **Consistent styling** with color and spacing systems  
✅ **Accessibility** through semantic HTML  
✅ **Validated schemas** that work with existing renderer  

### Current Renderer Capabilities

**Supported:**
- All layout components (container, grid, row, stack, card)
- Typography (heading, text, paragraph, link)
- Forms (input, textarea, select, checkbox, radio, button)
- Interactive (tabs, accordion, table, list, alert, badge)
- Navigation (breadcrumb, pagination)
- Styling via props and inline styles

**Limitations:**
- `paddingX`, `paddingY`, `marginX`, `marginY` are not standard CSS (use explicit properties or shorthand)
- Icons require specific icon library integration
- Charts require charting library integration
- Modals may have limited functionality
- Some advanced interactions may need custom handlers

### Implementation Notes

**No Code Changes Required:**
- All examples work with existing renderer
- All components verified against type definitions
- All props verified against implementation
- CSS converter handles standard CSS properties

**Model Training Focus:**
- Analyze policy content dynamically
- Select appropriate components for context
- Create professional, scannable layouts
- Follow format requirements strictly
- Generate semantic, accessible HTML

---

## Quick Reference

### Component Types
```
container, grid, row, column, stack, card, spacer, divider
heading, text, paragraph, link
button, badge, alert, icon, image
form, input, textarea, select, checkbox, radio, switch
tabs, accordion, modal, dropdown
table, list, metrics, progress, chart
nav, breadcrumb, pagination
```

### Required Props by Component
```
heading: content, level
text: content
paragraph: content
link: content, href
button: label
alert: message
input/textarea/select: name
list: items (array of objects with id and content)
table: columns, data
accordion/tabs: items
```

### Size Scale
```
xs: 0.75rem (12px)
sm: 0.875rem (14px)
base: 1rem (16px)
lg: 1.125rem (18px)
xl: 1.25rem (20px)
2xl: 1.5rem (24px)
3xl: 1.875rem (30px)
```

### Spacing Scale
```
0: 0
0.5: 0.125rem (2px)
1: 0.25rem (4px)
2: 0.5rem (8px)
3: 0.75rem (12px)
4: 1rem (16px)
6: 1.5rem (24px)
8: 2rem (32px)
12: 3rem (48px)
16: 4rem (64px)
```

### Container Max Widths
```
sm: 640px
md: 768px
lg: 1024px
xl: 1280px
2xl: 1536px
full: 100%
```

---

**End of Training Guide**

For detailed component specifications, see the full component registry section.  
For specific implementation examples, see the production example section.  
For error handling, see the validation section.

This guide enables cloud models to generate rich, professional, dynamic policy UIs that adapt to content while maintaining consistency, accessibility, and usability.
