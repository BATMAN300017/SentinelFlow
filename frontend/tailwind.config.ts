import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Strict institutional palette tokens
        obsidian: {
          950: '#080A08', // Main background
          900: '#0D100D', // Sidebar / Topbar
          850: '#121612', // Primary surfaces / cards
          800: '#181E18', // Elevated surfaces / hover
          750: '#1F261F', // Dropdowns / menus
          700: '#262D26', // Structural borders
          650: '#323B32', // Active borders / highlights
        },
        border: {
          subtle: '#1C221C',
          DEFAULT: '#262D26',
          strong: '#364036',
        },
        // Functional lime accents (5% distribution)
        lime: {
          DEFAULT: '#B7F34A',
          hover: '#C9FF65',
          active: '#9EE035',
          muted: 'rgba(183, 243, 74, 0.12)',
          border: 'rgba(183, 243, 74, 0.3)',
        },
        // Typography neutral distribution (25%)
        neutral: {
          primary: '#F2F4EF',
          secondary: '#929B90',
          muted: '#687166',
          faint: '#414840',
        },
        // Financial crime status colors (calibrated, disciplined)
        risk: {
          critical: '#FF4D4D',
          high: '#FF8833',
          medium: '#FFB800',
          low: '#B7F34A',
          neutral: '#687166',
        },
        // Institutional mapping for Tailwind slate utilities:
        // This instantly maps all 42 files and hundreds of components to the strict institutional palette!
        slate: {
          950: '#080A08', // Main background
          900: '#0D100D', // Primary structural container
          850: '#121612', // Card / Surface
          800: '#181E18', // Elevated surface
          750: '#1F261F', // Subtle border / hover
          700: '#262D26', // Standard border
          600: '#364036', // Strong border
          500: '#687166', // Muted text
          400: '#929B90', // Secondary text
          300: '#D5DAD3', // Light secondary text
          200: '#E8EBE6', // Light primary text
          100: '#F2F4EF', // Primary text
          50: '#FFFFFF',
        },
        // Institutional mapping for Tailwind emerald (maps to #B7F34A)
        emerald: {
          950: '#142010',
          900: '#1A2E16',
          800: '#29421E',
          700: '#3B5E2C',
          600: '#84C72B',
          500: '#B7F34A',
          400: '#B7F34A',
          300: '#C9FF65',
          200: '#E0FF9E',
          100: '#F1FFD6',
        },
      },
      fontFamily: {
        sans: ['Geist', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      boxShadow: {
        panel: '0 1px 2px 0 rgba(0, 0, 0, 0.45)',
        elevated: '0 4px 12px 0 rgba(0, 0, 0, 0.6)',
      },
    },
  },
  plugins: [],
};

export default config;
