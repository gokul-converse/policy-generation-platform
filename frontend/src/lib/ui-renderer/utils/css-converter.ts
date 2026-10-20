/**
 * CSS to Tailwind and Inline Style Converter
 * Converts CSS properties to Tailwind classes and inline styles
 */

import { CSSProperties } from '@/types/ui-schema';

interface ConvertedStyles {
  className: string;
  style: React.CSSProperties;
}

/**
 * Convert CSS properties to Tailwind classes and inline styles
 */
export function convertCSSToStyles(css: CSSProperties = {}): ConvertedStyles {
  const tailwindClasses: string[] = [];
  const inlineStyles: React.CSSProperties = {};

  // Display
  if (css.display) {
    const displayMap: Record<string, string> = {
      block: 'block',
      'inline-block': 'inline-block',
      inline: 'inline',
      flex: 'flex',
      'inline-flex': 'inline-flex',
      grid: 'grid',
      'inline-grid': 'inline-grid',
      none: 'hidden',
      hidden: 'hidden',
    };
    tailwindClasses.push(displayMap[css.display] || css.display);
  }

  // Position
  if (css.position) {
    tailwindClasses.push(css.position);
  }

  // Flexbox
  if (css.flexDirection) {
    const dirMap: Record<string, string> = {
      row: 'flex-row',
      'row-reverse': 'flex-row-reverse',
      column: 'flex-col',
      'column-reverse': 'flex-col-reverse',
    };
    tailwindClasses.push(dirMap[css.flexDirection] || `flex-${css.flexDirection}`);
  }

  if (css.flexWrap) {
    const wrapMap: Record<string, string> = {
      nowrap: 'flex-nowrap',
      wrap: 'flex-wrap',
      'wrap-reverse': 'flex-wrap-reverse',
    };
    tailwindClasses.push(wrapMap[css.flexWrap]);
  }

  if (css.justifyContent) {
    const justifyMap: Record<string, string> = {
      'flex-start': 'justify-start',
      'flex-end': 'justify-end',
      'center': 'justify-center',
      'space-between': 'justify-between',
      'space-around': 'justify-around',
      'space-evenly': 'justify-evenly',
      'stretch': 'justify-stretch',
      'start': 'justify-start',
      'end': 'justify-end',
      'between': 'justify-between',
      'around': 'justify-around',
      'evenly': 'justify-evenly',
    };
    const mapped = justifyMap[css.justifyContent];
    if (mapped) {
      tailwindClasses.push(mapped);
    } else {
      inlineStyles.justifyContent = css.justifyContent;
    }
  }

  if (css.alignItems) {
    const alignMap: Record<string, string> = {
      'stretch': 'items-stretch',
      'flex-start': 'items-start',
      'flex-end': 'items-end',
      'center': 'items-center',
      'baseline': 'items-baseline',
      'start': 'items-start',
      'end': 'items-end',
    };
    const mapped = alignMap[css.alignItems];
    if (mapped) {
      tailwindClasses.push(mapped);
    } else {
      inlineStyles.alignItems = css.alignItems;
    }
  }

  if (css.alignContent) {
    const alignContentMap: Record<string, string> = {
      'flex-start': 'content-start',
      'flex-end': 'content-end',
      'center': 'content-center',
      'space-between': 'content-between',
      'space-around': 'content-around',
      'space-evenly': 'content-evenly',
      'stretch': 'content-stretch',
      'start': 'content-start',
      'end': 'content-end',
      'between': 'content-between',
      'around': 'content-around',
      'evenly': 'content-evenly',
    };
    const mapped = alignContentMap[css.alignContent];
    if (mapped) {
      tailwindClasses.push(mapped);
    } else {
      inlineStyles.alignContent = css.alignContent;
    }
  }

  if (css.alignSelf) {
    const selfMap: Record<string, string> = {
      'auto': 'self-auto',
      'flex-start': 'self-start',
      'flex-end': 'self-end',
      'center': 'self-center',
      'stretch': 'self-stretch',
      'baseline': 'self-baseline',
      'start': 'self-start',
      'end': 'self-end',
    };
    const mapped = selfMap[css.alignSelf];
    if (mapped) {
      tailwindClasses.push(mapped);
    } else {
      inlineStyles.alignSelf = css.alignSelf;
    }
  }

  if (css.flex) {
    inlineStyles.flex = css.flex;
  }

  if (css.flexGrow !== undefined) {
    inlineStyles.flexGrow = css.flexGrow;
  }

  if (css.flexShrink !== undefined) {
    inlineStyles.flexShrink = css.flexShrink;
  }

  if (css.flexBasis !== undefined) {
    inlineStyles.flexBasis = css.flexBasis;
  }

  if (css.order !== undefined) {
    inlineStyles.order = css.order;
  }

  // Gap - handle rem and other CSS units
  if (css.gap !== undefined) {
    inlineStyles.gap = css.gap;
  }

  if (css.columnGap !== undefined) {
    inlineStyles.columnGap = css.columnGap;
  }

  if (css.rowGap !== undefined) {
    inlineStyles.rowGap = css.rowGap;
  }

  // Spacing - handle rem and other CSS units
  const spacingProps = ['margin', 'marginTop', 'marginRight', 'marginBottom', 'marginLeft',
    'padding', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft'];

  spacingProps.forEach((prop) => {
    const value = (css as any)[prop];
    if (value !== undefined) {
      (inlineStyles as any)[prop] = value;
    }
  });

  // Handle spacing shortcuts (marginX, marginY, paddingX, paddingY)
  if (css.marginX !== undefined) {
    inlineStyles.marginLeft = css.marginX;
    inlineStyles.marginRight = css.marginX;
  }
  if (css.marginY !== undefined) {
    inlineStyles.marginTop = css.marginY;
    inlineStyles.marginBottom = css.marginY;
  }
  if (css.paddingX !== undefined) {
    inlineStyles.paddingLeft = css.paddingX;
    inlineStyles.paddingRight = css.paddingX;
  }
  if (css.paddingY !== undefined) {
    inlineStyles.paddingTop = css.paddingY;
    inlineStyles.paddingBottom = css.paddingY;
  }

  // Sizing
  if (css.width !== undefined) {
    if (css.width === 'full') tailwindClasses.push('w-full');
    else if (css.width === 'screen') tailwindClasses.push('w-screen');
    else if (css.width === 'auto') tailwindClasses.push('w-auto');
    else inlineStyles.width = css.width;
  }

  if (css.height !== undefined) {
    if (css.height === 'full') tailwindClasses.push('h-full');
    else if (css.height === 'screen') tailwindClasses.push('h-screen');
    else if (css.height === 'auto') tailwindClasses.push('h-auto');
    else inlineStyles.height = css.height;
  }

  if (css.minWidth !== undefined) inlineStyles.minWidth = css.minWidth;
  if (css.maxWidth !== undefined) {
    if (typeof css.maxWidth === 'string' && ['xs', 'sm', 'md', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl', '6xl', '7xl'].includes(css.maxWidth)) {
      tailwindClasses.push(`max-w-${css.maxWidth}`);
    } else {
      inlineStyles.maxWidth = css.maxWidth;
    }
  }
  if (css.minHeight !== undefined) inlineStyles.minHeight = css.minHeight;
  if (css.maxHeight !== undefined) inlineStyles.maxHeight = css.maxHeight;

  // Positioning
  if (css.top !== undefined) inlineStyles.top = css.top;
  if (css.right !== undefined) inlineStyles.right = css.right;
  if (css.bottom !== undefined) inlineStyles.bottom = css.bottom;
  if (css.left !== undefined) inlineStyles.left = css.left;
  if (css.inset !== undefined) inlineStyles.inset = css.inset;
  if (css.zIndex !== undefined) {
    if (css.zIndex >= 0 && css.zIndex <= 50 && css.zIndex % 10 === 0) {
      tailwindClasses.push(`z-${css.zIndex}`);
    } else {
      inlineStyles.zIndex = css.zIndex;
    }
  }

  // Typography
  if (css.fontSize !== undefined) inlineStyles.fontSize = css.fontSize;
  if (css.fontWeight !== undefined) {
    inlineStyles.fontWeight = css.fontWeight;
  }
  if (css.fontFamily) inlineStyles.fontFamily = css.fontFamily;
  if (css.lineHeight !== undefined) inlineStyles.lineHeight = css.lineHeight;
  if (css.letterSpacing !== undefined) inlineStyles.letterSpacing = css.letterSpacing;

  if (css.textAlign) {
    tailwindClasses.push(`text-${css.textAlign}`);
  }

  if (css.textTransform) {
    if (css.textTransform === 'none') tailwindClasses.push('normal-case');
    else if (css.textTransform === 'uppercase') tailwindClasses.push('uppercase');
    else if (css.textTransform === 'lowercase') tailwindClasses.push('lowercase');
    else if (css.textTransform === 'capitalize') tailwindClasses.push('capitalize');
  }

  if (css.textDecoration) inlineStyles.textDecoration = css.textDecoration;
  if (css.fontStyle) {
    if (css.fontStyle === 'italic') tailwindClasses.push('italic');
    else if (css.fontStyle === 'normal') tailwindClasses.push('not-italic');
  }
  if (css.whiteSpace) inlineStyles.whiteSpace = css.whiteSpace;
  if (css.wordBreak) inlineStyles.wordBreak = css.wordBreak;

  // Colors
  if (css.color) inlineStyles.color = css.color;
  if (css.backgroundColor) inlineStyles.backgroundColor = css.backgroundColor;
  if (css.borderColor) inlineStyles.borderColor = css.borderColor;
  if (css.opacity !== undefined) {
    if (css.opacity >= 0 && css.opacity <= 1) {
      const opacityValue = Math.round(css.opacity * 100);
      tailwindClasses.push(`opacity-${opacityValue}`);
    } else {
      inlineStyles.opacity = css.opacity;
    }
  }

  // Borders
  if (css.border) inlineStyles.border = css.border;
  if (css.borderTop) inlineStyles.borderTop = css.borderTop;
  if (css.borderRight) inlineStyles.borderRight = css.borderRight;
  if (css.borderBottom) inlineStyles.borderBottom = css.borderBottom;
  if (css.borderLeft) inlineStyles.borderLeft = css.borderLeft;
  if (css.borderWidth !== undefined) inlineStyles.borderWidth = css.borderWidth;
  if (css.borderStyle) inlineStyles.borderStyle = css.borderStyle;
  if (css.borderRadius !== undefined) {
    inlineStyles.borderRadius = css.borderRadius;
  }
  if (css.borderTopLeftRadius !== undefined) inlineStyles.borderTopLeftRadius = css.borderTopLeftRadius;
  if (css.borderTopRightRadius !== undefined) inlineStyles.borderTopRightRadius = css.borderTopRightRadius;
  if (css.borderBottomLeftRadius !== undefined) inlineStyles.borderBottomLeftRadius = css.borderBottomLeftRadius;
  if (css.borderBottomRightRadius !== undefined) inlineStyles.borderBottomRightRadius = css.borderBottomRightRadius;

  // Effects
  if (css.boxShadow) inlineStyles.boxShadow = css.boxShadow;
  if (css.textShadow) inlineStyles.textShadow = css.textShadow;
  if (css.background) inlineStyles.background = css.background;
  if (css.backgroundImage) inlineStyles.backgroundImage = css.backgroundImage;
  if (css.backgroundSize) inlineStyles.backgroundSize = css.backgroundSize;
  if (css.backgroundPosition) inlineStyles.backgroundPosition = css.backgroundPosition;
  if (css.backgroundRepeat) inlineStyles.backgroundRepeat = css.backgroundRepeat;

  // Overflow
  if (css.overflow) tailwindClasses.push(`overflow-${css.overflow}`);
  if (css.overflowX) tailwindClasses.push(`overflow-x-${css.overflowX}`);
  if (css.overflowY) tailwindClasses.push(`overflow-y-${css.overflowY}`);

  // Transform
  if (css.transform) inlineStyles.transform = css.transform;
  if (css.transformOrigin) inlineStyles.transformOrigin = css.transformOrigin;

  // Transition and Animation
  if (css.transition) inlineStyles.transition = css.transition;
  if (css.animation) inlineStyles.animation = css.animation;

  // Cursor and Interaction
  if (css.cursor) {
    const cursorMap: Record<string, string> = {
      pointer: 'cursor-pointer',
      default: 'cursor-default',
      move: 'cursor-move',
      wait: 'cursor-wait',
      text: 'cursor-text',
      'not-allowed': 'cursor-not-allowed',
    };
    tailwindClasses.push(cursorMap[css.cursor] || `cursor-${css.cursor}`);
  }

  if (css.pointerEvents) tailwindClasses.push(`pointer-events-${css.pointerEvents}`);
  if (css.userSelect) inlineStyles.userSelect = css.userSelect;

  // Grid
  if (css.gridTemplateColumns) inlineStyles.gridTemplateColumns = css.gridTemplateColumns;
  if (css.gridTemplateRows) inlineStyles.gridTemplateRows = css.gridTemplateRows;
  if (css.gridColumn) inlineStyles.gridColumn = css.gridColumn;
  if (css.gridRow) inlineStyles.gridRow = css.gridRow;
  if (css.gridAutoFlow) inlineStyles.gridAutoFlow = css.gridAutoFlow;
  if (css.gridAutoColumns) inlineStyles.gridAutoColumns = css.gridAutoColumns;
  if (css.gridAutoRows) inlineStyles.gridAutoRows = css.gridAutoRows;
  if (css.gridColumnStart) inlineStyles.gridColumnStart = css.gridColumnStart;
  if (css.gridColumnEnd) inlineStyles.gridColumnEnd = css.gridColumnEnd;
  if (css.gridRowStart) inlineStyles.gridRowStart = css.gridRowStart;
  if (css.gridRowEnd) inlineStyles.gridRowEnd = css.gridRowEnd;

  // Other
  if (css.visibility) tailwindClasses.push(css.visibility);
  if (css.objectFit) tailwindClasses.push(`object-${css.objectFit}`);

  return {
    className: tailwindClasses.join(' '),
    style: inlineStyles,
  };
}

/**
 * Merge styles with existing className and style props
 */
export function mergeStyles(
  baseClassName: string = '',
  baseStyle: React.CSSProperties = {},
  css?: CSSProperties
): { className: string; style: React.CSSProperties } {
  if (!css) {
    return { className: baseClassName, style: baseStyle };
  }

  const converted = convertCSSToStyles(css);

  return {
    className: `${baseClassName} ${converted.className}`.trim(),
    style: { ...baseStyle, ...converted.style },
  };
}
