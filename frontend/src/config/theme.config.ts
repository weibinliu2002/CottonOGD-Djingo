/**
 * Theme Configuration
 * Centralized configuration for images, colors, and branding assets
 * Easy to update images and colors in one place
 */

// Image Assets Configuration
export const images = {
  // Branding
  logo: '@/assets/images/logo.svg',
  favicon: '@/assets/images/favicon.png',
  
  // Hero Section Background (can be replaced with any image)
  heroBackground: '@/assets/images/mh.png',
  
  // Feature Images (for cards and sections)
  featureGenome: '@/assets/images/egg.jpg',
  featureAnalysis: '@/assets/images/mh.png',
  featureVisualization: '@/assets/images/screenshot-dashboard.png',
  
  // Screenshots for demos
  demoDashboard: '@/assets/images/screenshot-dashboard.png',
  demoSearch: '@/assets/images/screenshot-search.png',
  
  // Placeholder images (can be added later)
  placeholder404: '@/assets/images/mh.png',
  placeholderComingSoon: '@/assets/images/mh.png',
} as const

// Color Palette Configuration
export const colors = {
  // Primary Colors
  primary: {
    main: '#3a6ea5',      // Main brand blue
    light: '#7297bd',     // Lighter blue for gradients
    dark: '#2f5f94',      // Darker blue for emphasis
    contrast: '#ffffff',  // White text on primary
  },
  
  // Secondary Colors
  secondary: {
    main: '#466686',      // Muted blue-gray
    light: '#5a81a8',     // Light accent
    dark: '#355a80',      // Dark accent
  },
  
  // Accent Colors (for highlights and CTAs)
  accent: {
    orange: '#ff7b29',    // Warm accent for buttons
    green: '#52c41a',     // Success states
    red: '#ff4d4f',       // Error states
    yellow: '#faad14',    // Warning states
  },
  
  // Neutral Colors
  neutral: {
    white: '#ffffff',
    gray50: '#fafafa',
    gray100: '#f5f5f5',
    gray200: '#e9ecef',
    gray300: '#d9d9d9',
    gray400: '#bfbfbf',
    gray500: '#8c8c8c',
    gray600: '#6c757d',
    gray700: '#495057',
    gray800: '#333333',
    gray900: '#1a1a1a',
  },
  
  // Gradient Presets
  gradients: {
    hero: 'linear-gradient(135deg, #3a6ea5 0%, #7297bd 100%)',
    card: 'linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%)',
    button: 'linear-gradient(90deg, #3a6ea5 0%, #7297bd 100%)',
  },
} as const

// Typography Configuration
export const typography = {
  fontFamily: {
    primary: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: '"SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace',
  },
  
  fontSize: {
    xs: '12px',
    sm: '14px',
    base: '16px',
    lg: '18px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '32px',
    '4xl': '48px',
  },
  
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
} as const

// Spacing System (in pixels)
export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  '2xl': '48px',
  '3xl': '64px',
} as const

// Border Radius
export const borderRadius = {
  none: '0',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  full: '9999px',
} as const

// Shadows
export const shadows = {
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
} as const

// Transitions
export const transitions = {
  fast: '150ms ease-in-out',
  base: '200ms ease-in-out',
  slow: '300ms ease-in-out',
} as const

// Export default theme object
export const theme = {
  colors,
  typography,
  spacing,
  borderRadius,
  shadows,
  transitions,
} as const

export type Theme = typeof theme
export type Colors = typeof colors
export type Images = typeof images
