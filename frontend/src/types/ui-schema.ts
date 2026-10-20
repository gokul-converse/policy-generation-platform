/**
 * JSON UI Schema Types
 * Type-safe definitions for JSON-driven UI components
 */

// ============================================================================
// Core Schema Types
// ============================================================================

export type ComponentType =
  // Layout Components
  | 'container'
  | 'row'
  | 'column'
  | 'grid'
  | 'stack'
  | 'spacer'
  // Typography & Content
  | 'text'
  | 'heading'
  | 'paragraph'
  | 'link'
  // UI Elements
  | 'button'
  | 'badge'
  | 'alert'
  | 'card'
  | 'divider'
  | 'image'
  | 'icon'
  // Form Elements
  | 'form'
  | 'input'
  | 'textarea'
  | 'select'
  | 'checkbox'
  | 'radio'
  | 'switch'
  // Interactive Components
  | 'accordion'
  | 'tabs'
  | 'modal'
  | 'dropdown'
  // Data Display
  | 'table'
  | 'list'
  | 'metrics'
  | 'chart'
  | 'progress'
  // Navigation
  | 'nav'
  | 'breadcrumb'
  | 'pagination';

export type ResponsiveValue<T> = T | {
  base?: T;
  sm?: T;
  md?: T;
  lg?: T;
  xl?: T;
};

export type ColorVariant = 
  | 'primary' 
  | 'secondary' 
  | 'success' 
  | 'danger' 
  | 'warning' 
  | 'info'
  | 'default'
  | 'muted';

export type SizeVariant = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

// ============================================================================
// Component Props Interface
// ============================================================================

// CSS Style System
export interface CSSProperties {
  // Layout
  display?: 'block' | 'inline-block' | 'inline' | 'flex' | 'inline-flex' | 'grid' | 'inline-grid' | 'none' | 'hidden';
  position?: 'static' | 'relative' | 'absolute' | 'fixed' | 'sticky';
  
  // Flexbox
  flexDirection?: 'row' | 'row-reverse' | 'column' | 'column-reverse';
  flexWrap?: 'nowrap' | 'wrap' | 'wrap-reverse';
  justifyContent?: 'start' | 'end' | 'center' | 'between' | 'around' | 'evenly' | 'stretch';
  alignItems?: 'start' | 'end' | 'center' | 'baseline' | 'stretch';
  alignContent?: 'start' | 'end' | 'center' | 'between' | 'around' | 'evenly' | 'stretch';
  alignSelf?: 'auto' | 'start' | 'end' | 'center' | 'stretch' | 'baseline';
  flex?: string; // e.g., "1", "1 1 auto", "none"
  flexGrow?: number;
  flexShrink?: number;
  flexBasis?: string;
  order?: number;
  
  // Grid
  gridTemplateColumns?: string;
  gridTemplateRows?: string;
  gridTemplateAreas?: string;
  gridAutoColumns?: string;
  gridAutoRows?: string;
  gridAutoFlow?: 'row' | 'column' | 'dense' | 'row dense' | 'column dense';
  gridColumn?: string;
  gridRow?: string;
  gridColumnStart?: string | number;
  gridColumnEnd?: string | number;
  gridRowStart?: string | number;
  gridRowEnd?: string | number;
  gap?: string | number;
  columnGap?: string | number;
  rowGap?: string | number;
  
  // Spacing
  margin?: string | number;
  marginTop?: string | number;
  marginRight?: string | number;
  marginBottom?: string | number;
  marginLeft?: string | number;
  marginX?: string | number; // Tailwind-style
  marginY?: string | number; // Tailwind-style
  padding?: string | number;
  paddingTop?: string | number;
  paddingRight?: string | number;
  paddingBottom?: string | number;
  paddingLeft?: string | number;
  paddingX?: string | number; // Tailwind-style
  paddingY?: string | number; // Tailwind-style
  space?: number; // Space between children (Tailwind-style)
  spaceX?: number;
  spaceY?: number;
  
  // Sizing
  width?: string | number;
  minWidth?: string | number;
  maxWidth?: string | number;
  height?: string | number;
  minHeight?: string | number;
  maxHeight?: string | number;
  
  // Positioning
  top?: string | number;
  right?: string | number;
  bottom?: string | number;
  left?: string | number;
  inset?: string | number;
  zIndex?: number;
  
  // Typography
  fontSize?: string | number;
  fontWeight?: number | 'normal' | 'bold' | 'bolder' | 'lighter';
  fontFamily?: string;
  lineHeight?: string | number;
  letterSpacing?: string | number;
  textAlign?: 'left' | 'center' | 'right' | 'justify' | 'start' | 'end';
  textTransform?: 'none' | 'uppercase' | 'lowercase' | 'capitalize';
  textDecoration?: string;
  fontStyle?: 'normal' | 'italic' | 'oblique';
  whiteSpace?: 'normal' | 'nowrap' | 'pre' | 'pre-wrap' | 'pre-line';
  wordBreak?: 'normal' | 'break-all' | 'keep-all' | 'break-word';
  
  // Colors
  color?: string;
  backgroundColor?: string;
  borderColor?: string;
  opacity?: number;
  
  // Borders
  border?: string;
  borderWidth?: string | number;
  borderStyle?: 'solid' | 'dashed' | 'dotted' | 'double' | 'none';
  borderRadius?: string | number;
  borderTop?: string;
  borderRight?: string;
  borderBottom?: string;
  borderLeft?: string;
  borderTopWidth?: string | number;
  borderRightWidth?: string | number;
  borderBottomWidth?: string | number;
  borderLeftWidth?: string | number;
  borderTopLeftRadius?: string | number;
  borderTopRightRadius?: string | number;
  borderBottomLeftRadius?: string | number;
  borderBottomRightRadius?: string | number;
  
  // Effects
  boxShadow?: string;
  textShadow?: string;
  background?: string;
  backgroundImage?: string;
  backgroundSize?: string;
  backgroundPosition?: string;
  backgroundRepeat?: string;
  backdropFilter?: string;
  filter?: string;
  
  // Overflow
  overflow?: 'visible' | 'hidden' | 'scroll' | 'auto';
  overflowX?: 'visible' | 'hidden' | 'scroll' | 'auto';
  overflowY?: 'visible' | 'hidden' | 'scroll' | 'auto';
  
  // Transform
  transform?: string;
  transformOrigin?: string;
  
  // Transition
  transition?: string;
  transitionProperty?: string;
  transitionDuration?: string;
  transitionTimingFunction?: string;
  transitionDelay?: string;
  animation?: string;
  
  // Cursor
  cursor?: string;
  pointerEvents?: 'auto' | 'none';
  userSelect?: 'auto' | 'none' | 'text' | 'all';
  
  // Other
  visibility?: 'visible' | 'hidden' | 'collapse';
  objectFit?: 'contain' | 'cover' | 'fill' | 'none' | 'scale-down';
  objectPosition?: string;
}

export interface BaseComponentProps {
  id?: string;
  className?: string;
  style?: CSSProperties;
  css?: CSSProperties; // Alternative prop name
  hidden?: boolean;
  testId?: string;
}

// Layout Props
export interface ContainerProps extends BaseComponentProps {
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  padding?: ResponsiveValue<number>;
  centered?: boolean;
}

export interface GridProps extends BaseComponentProps {
  columns?: ResponsiveValue<number>;
  gap?: number;
  alignItems?: 'start' | 'center' | 'end' | 'stretch';
}

export interface RowProps extends BaseComponentProps {
  gap?: number;
  justify?: 'start' | 'center' | 'end' | 'between' | 'around';
  align?: 'start' | 'center' | 'end' | 'stretch';
  wrap?: boolean;
}

export interface ColumnProps extends BaseComponentProps {
  span?: ResponsiveValue<number>;
  gap?: number;
}

export interface StackProps extends BaseComponentProps {
  direction?: 'vertical' | 'horizontal';
  gap?: number;
  align?: 'start' | 'center' | 'end' | 'stretch';
}

// Typography Props
export interface TextProps extends BaseComponentProps {
  content: string;
  variant?: 'body' | 'caption' | 'overline';
  size?: SizeVariant;
  weight?: 'normal' | 'medium' | 'semibold' | 'bold';
  color?: string;
  align?: 'left' | 'center' | 'right' | 'justify';
}

export interface HeadingProps extends BaseComponentProps {
  content: string;
  level?: 1 | 2 | 3 | 4 | 5 | 6;
  size?: SizeVariant;
  weight?: 'normal' | 'medium' | 'semibold' | 'bold';
}

export interface LinkProps extends BaseComponentProps {
  href: string;
  content: string;
  external?: boolean;
  underline?: boolean;
}

// UI Element Props
export interface ButtonProps extends BaseComponentProps {
  label: string;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: SizeVariant;
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  onClick?: string; // Action ID
}

export interface BadgeProps extends BaseComponentProps {
  label: string;
  variant?: ColorVariant;
  size?: SizeVariant;
  rounded?: boolean;
}

export interface AlertProps extends BaseComponentProps {
  message: string;
  title?: string;
  variant?: 'info' | 'success' | 'warning' | 'error';
  dismissible?: boolean;
}

export interface CardProps extends BaseComponentProps {
  title?: string;
  subtitle?: string;
  variant?: 'default' | 'bordered' | 'elevated';
  hoverable?: boolean;
  padding?: number;
}

export interface DividerProps extends BaseComponentProps {
  orientation?: 'horizontal' | 'vertical';
  variant?: 'solid' | 'dashed' | 'dotted';
}

export interface ImageProps extends BaseComponentProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  rounded?: boolean;
  objectFit?: 'contain' | 'cover' | 'fill' | 'none';
}

// Form Props
export interface FormProps extends BaseComponentProps {
  onSubmit?: string; // Action ID
  validationMode?: 'onSubmit' | 'onChange' | 'onBlur';
}

export interface InputProps extends BaseComponentProps {
  name: string;
  label?: string;
  placeholder?: string;
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'date';
  defaultValue?: string;
  required?: boolean;
  disabled?: boolean;
  validation?: ValidationRule[];
  helperText?: string;
  errorMessage?: string;
}

export interface TextareaProps extends BaseComponentProps {
  name: string;
  label?: string;
  placeholder?: string;
  rows?: number;
  defaultValue?: string;
  required?: boolean;
  disabled?: boolean;
  validation?: ValidationRule[];
  helperText?: string;
  maxLength?: number;
}

export interface SelectProps extends BaseComponentProps {
  name: string;
  label?: string;
  placeholder?: string;
  options: Array<{ label: string; value: string }>;
  defaultValue?: string;
  required?: boolean;
  disabled?: boolean;
  multiple?: boolean;
}

export interface CheckboxProps extends BaseComponentProps {
  name: string;
  label: string;
  defaultChecked?: boolean;
  disabled?: boolean;
  required?: boolean;
}

export interface RadioProps extends BaseComponentProps {
  name: string;
  label: string;
  value: string;
  defaultChecked?: boolean;
  disabled?: boolean;
}

// Interactive Component Props
export interface AccordionProps extends BaseComponentProps {
  items: Array<{
    id: string;
    title: string;
    content: UIComponentSchema | UIComponentSchema[];
  }>;
  allowMultiple?: boolean;
  defaultOpen?: string[];
}

export interface TabsProps extends BaseComponentProps {
  items: Array<{
    id: string;
    label: string;
    content: UIComponentSchema | UIComponentSchema[];
  }>;
  defaultTab?: string;
  variant?: 'line' | 'enclosed' | 'soft';
}

// Data Display Props
export interface TableProps extends BaseComponentProps {
  columns: Array<{
    key: string;
    label: string;
    width?: string;
    align?: 'left' | 'center' | 'right';
  }>;
  data: Record<string, any>[] | string; // Array or data binding key
  striped?: boolean;
  hoverable?: boolean;
  compact?: boolean;
}

export interface ListProps extends BaseComponentProps {
  items: Array<{
    id: string;
    content: string | UIComponentSchema;
  }>;
  variant?: 'plain' | 'bullet' | 'numbered' | 'icon';
  spacing?: number;
}

export interface MetricsProps extends BaseComponentProps {
  items: Array<{
    label: string;
    value: string | number;
    trend?: 'up' | 'down' | 'neutral';
    trendValue?: string;
    icon?: string;
  }>;
  columns?: ResponsiveValue<number>;
}

export interface ChartProps extends BaseComponentProps {
  type: 'line' | 'bar' | 'pie' | 'donut';
  data: any[] | string; // Data array or binding key
  title?: string;
  height?: number;
}

export interface ProgressProps extends BaseComponentProps {
  value: number;
  max?: number;
  label?: string;
  showValue?: boolean;
  variant?: ColorVariant;
  size?: SizeVariant;
}

// Navigation Props
export interface NavProps extends BaseComponentProps {
  items: Array<{
    label: string;
    href: string;
    active?: boolean;
    icon?: string;
  }>;
  variant?: 'horizontal' | 'vertical';
}

export interface BreadcrumbProps extends BaseComponentProps {
  items: Array<{
    label: string;
    href?: string;
  }>;
  separator?: string;
}

export interface PaginationProps extends BaseComponentProps {
  currentPage: number;
  totalPages: number;
  onPageChange?: string; // Action ID
  showFirstLast?: boolean;
}

// ============================================================================
// Validation
// ============================================================================

export interface ValidationRule {
  type: 'required' | 'minLength' | 'maxLength' | 'pattern' | 'email' | 'url' | 'custom';
  value?: any;
  message: string;
}

// ============================================================================
// Actions & Data Binding
// ============================================================================

export interface ActionDefinition {
  id: string;
  type: 'navigate' | 'api' | 'setState' | 'submit' | 'custom';
  config: Record<string, any>;
}

export interface DataSource {
  id: string;
  type: 'api' | 'static' | 'computed';
  config: APIConfig | StaticConfig | ComputedConfig;
}

export interface APIConfig {
  endpoint: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: Record<string, any>;
  transformResponse?: string; // Function body as string
}

export interface StaticConfig {
  data: any;
}

export interface ComputedConfig {
  dependencies: string[];
  compute: string; // Function body as string
}

// ============================================================================
// Main Schema
// ============================================================================

export interface UIComponentSchema {
  type: ComponentType;
  props?: Record<string, any>;
  children?: UIComponentSchema[];
  binding?: string; // Data binding key
  condition?: string; // Conditional rendering expression
}

export interface UISchema {
  version: string;
  metadata?: {
    title?: string;
    description?: string;
    author?: string;
    createdAt?: string;
  };
  dataSources?: DataSource[];
  actions?: ActionDefinition[];
  components: UIComponentSchema[];
}

// ============================================================================
// Type Guards
// ============================================================================

export function isUISchema(obj: any): obj is UISchema {
  return (
    obj &&
    typeof obj === 'object' &&
    typeof obj.version === 'string' &&
    Array.isArray(obj.components)
  );
}

export function isUIComponentSchema(obj: any): obj is UIComponentSchema {
  return (
    obj &&
    typeof obj === 'object' &&
    typeof obj.type === 'string' &&
    (!obj.children || Array.isArray(obj.children))
  );
}
